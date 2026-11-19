"""Monta os dashes da Champion para o GitHub Pages.

Lê config/dashes.json, busca o Meta pela API (token em META_TOKEN), junta o Google
que o script da MCC grava em data/google.json e escreve o site em site/.
Só usa a biblioteca padrão do Python.
"""
import datetime as dt
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = 'https://graph.facebook.com/'
CAMPOS = 'campaign_id,campaign_name,spend,impressions,inline_link_clicks,clicks,actions'


def agora_local(fuso):
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(fuso))
    except Exception:
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))


def http_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'champion-dashes'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except Exception:
            return {'error': {'message': 'HTTP %s' % e.code}}


def meta_lista(caminho, params, token):
    url = GRAPH + caminho + '?' + urllib.parse.urlencode(dict(params, access_token=token))
    saida = []
    while url:
        js = http_json(url)
        if 'error' in js:
            raise RuntimeError(js['error'].get('message', 'erro do Meta'))
        saida += js.get('data', [])
        url = (js.get('paging') or {}).get('next')
    return saida


def leads_de(acoes):
    por_tipo = {a.get('action_type'): float(a.get('value', 0)) for a in (acoes or [])}
    if 'lead' in por_tipo:
        return por_tipo['lead']
    return por_tipo.get('onsite_conversion.lead_grouped', 0.0)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def soma(linhas):
    t = {'gasto': 0.0, 'impressoes': 0, 'cliques': 0, 'cliques_todos': 0, 'leads': 0.0}
    for r in linhas:
        t['gasto'] += r['gasto']
        t['impressoes'] += r['impressoes']
        t['cliques'] += r['cliques']
        t['cliques_todos'] += r['cliques_todos']
        t['leads'] += r['leads']
    t['gasto'] = round(t['gasto'], 2)
    t['leads'] = round(t['leads'])
    t['cpl'] = round(t['gasto'] / t['leads'], 2) if t['leads'] else None
    t['cpc'] = round(t['gasto'] / t['cliques_todos'], 2) if t['cliques_todos'] else None
    return t


def coletar_meta(d, periodo, token):
    conta = 'act_' + d['meta_conta']
    filtro = []
    if d.get('filtro_campanha'):
        f = d['filtro_campanha']
        filtro = [{'field': 'campaign.name', 'operator': f['operador'], 'value': f['texto']}]
    base = {'level': 'campaign', 'limit': 500}
    if filtro:
        base['filtering'] = json.dumps(filtro)

    info = http_json(GRAPH + conta + '?' + urllib.parse.urlencode({'fields': 'name', 'access_token': token}))
    if 'error' in info:
        raise RuntimeError(info['error'].get('message', 'erro do Meta'))

    tr = json.dumps({'since': periodo['ant_inicio'], 'until': periodo['fim']})
    linhas = meta_lista(conta + '/insights', dict(base, fields=CAMPOS, time_range=tr, time_increment=1), token)
    dias = []
    for r in linhas:
        dias.append({'data': r['date_start'], 'id': r.get('campaign_id'), 'nome': r.get('campaign_name'),
                     'gasto': num(r.get('spend')), 'impressoes': int(num(r.get('impressions'))),
                     'cliques': int(num(r.get('inline_link_clicks'))), 'cliques_todos': int(num(r.get('clicks'))),
                     'leads': leads_de(r.get('actions'))})
    atual = [x for x in dias if x['data'] >= periodo['inicio']]
    anterior = [x for x in dias if periodo['ant_inicio'] <= x['data'] <= periodo['ant_fim']]

    diario = []
    dia = dt.date.fromisoformat(periodo['inicio'])
    fim = dt.date.fromisoformat(periodo['fim'])
    while dia <= fim:
        s = soma([x for x in atual if x['data'] == dia.isoformat()])
        diario.append({'data': dia.isoformat(), 'gasto': s['gasto'], 'leads': s['leads']})
        dia += dt.timedelta(days=1)

    camp = {}
    for x in atual:
        c = camp.setdefault(x['id'], {'id': x['id'], 'nome': x['nome'], 'linhas': []})
        c['linhas'].append(x)
    status = {}
    ids = [i for i in camp if i]
    for k in range(0, len(ids), 50):
        js = http_json(GRAPH + '?' + urllib.parse.urlencode({'ids': ','.join(ids[k:k + 50]), 'fields': 'effective_status', 'access_token': token}))
        for i, v in js.items():
            if isinstance(v, dict):
                status[i] = v.get('effective_status')
    campanhas = []
    for c in camp.values():
        s = soma(c['linhas'])
        if s['gasto'] <= 0:
            continue
        campanhas.append({'id': c['id'], 'nome': c['nome'], 'status': 'Ativo' if status.get(c['id']) == 'ACTIVE' else 'Inativo',
                          'gasto': s['gasto'], 'impressoes': s['impressoes'], 'cliques': s['cliques'], 'leads': s['leads'], 'cpl': s['cpl']})
    campanhas.sort(key=lambda c: -c['gasto'])

    tr_atual = json.dumps({'since': periodo['inicio'], 'until': periodo['fim']})
    idade = {}
    for r in meta_lista(conta + '/insights', dict(base, fields='campaign_id,actions', time_range=tr_atual, breakdowns='age'), token):
        idade[r.get('age')] = idade.get(r.get('age'), 0) + leads_de(r.get('actions'))
    pos = {}
    for r in meta_lista(conta + '/insights', dict(base, fields='campaign_id,actions', time_range=tr_atual, breakdowns='publisher_platform,platform_position'), token):
        k = (r.get('publisher_platform'), r.get('platform_position'))
        pos[k] = pos.get(k, 0) + leads_de(r.get('actions'))

    return {
        'conta_nome': info.get('name'), 'conta_id': d['meta_conta'],
        'atual': soma(atual), 'anterior': soma(anterior), 'diario': diario, 'campanhas': campanhas,
        'idade': [{'faixa': k, 'leads': round(v)} for k, v in sorted(idade.items()) if v > 0],
        'posicionamento': [{'plataforma': k[0], 'posicao': k[1], 'leads': round(v)} for k, v in sorted(pos.items(), key=lambda i: -i[1]) if v > 0],
    }


def juntar_google(d, google):
    contas = d.get('google_contas') or []
    if not contas:
        return None
    if not google:
        return {'sem_dados': True}
    achadas = [google['contas'][c] for c in contas if c in google.get('contas', {})]
    if not achadas:
        return {'sem_dados': True}
    por_dia = {}
    for c in achadas:
        for r in c.get('diario', []):
            k = (r['data'], r['periodo'])
            t = por_dia.setdefault(k, {'data': r['data'], 'periodo': r['periodo'], 'gasto': 0.0, 'impressoes': 0, 'cliques': 0, 'conversoes': 0.0})
            t['gasto'] += num(r.get('gasto'))
            t['impressoes'] += int(num(r.get('impressoes')))
            t['cliques'] += int(num(r.get('cliques')))
            t['conversoes'] += num(r.get('conversoes'))
    diario = sorted(por_dia.values(), key=lambda r: r['data'])

    def tot(per):
        rs = [r for r in diario if r['periodo'] == per]
        g = round(sum(r['gasto'] for r in rs), 2)
        cl = sum(r['cliques'] for r in rs)
        cv = round(sum(r['conversoes'] for r in rs), 2)
        return {'gasto': g, 'impressoes': sum(r['impressoes'] for r in rs), 'cliques': cl, 'conversoes': cv,
                'cpc': round(g / cl, 2) if cl else None, 'cpa': round(g / cv, 2) if cv else None}

    campanhas = []
    for c in achadas:
        campanhas += c.get('campanhas', [])
    campanhas.sort(key=lambda c: -num(c.get('gasto')))
    return {'contas': [(c.get('nome') or '') + ' · ' + k for k, c in zip([x for x in contas if x in google['contas']], achadas)],
            'atualizado': google.get('atualizado'), 'atual': tot('atual'), 'anterior': tot('anterior'),
            'diario': [r for r in diario if r['periodo'] == 'atual'], 'campanhas': campanhas}


def main():
    cfg = json.load(open(os.path.join(RAIZ, 'config', 'dashes.json'), encoding='utf-8'))
    geral = os.environ.get('META_TOKEN', '').strip()
    algum_token = False
    agora = agora_local(cfg.get('fuso', 'America/Sao_Paulo'))
    hoje = agora.date()
    inicio = hoje.replace(day=1)
    n = (hoje - inicio).days + 1
    ant_fim = inicio - dt.timedelta(days=1)
    ant_inicio = ant_fim - dt.timedelta(days=n - 1)
    periodo = {'inicio': inicio.isoformat(), 'fim': hoje.isoformat(), 'ant_inicio': ant_inicio.isoformat(), 'ant_fim': ant_fim.isoformat()}

    gpath = os.path.join(RAIZ, 'data', 'google.json')
    google = json.load(open(gpath, encoding='utf-8')) if os.path.exists(gpath) else None

    site = os.path.join(RAIZ, 'site')
    if os.path.exists(site):
        shutil.rmtree(site)
    os.makedirs(site)
    modelo = open(os.path.join(RAIZ, 'modelo', 'dash.html'), encoding='utf-8').read()
    hub = open(os.path.join(RAIZ, 'modelo', 'hub.html'), encoding='utf-8').read()
    falhas = 0
    itens = []
    for d in cfg['dashes']:
        saida = {'slug': d['slug'], 'nome': d['nome'], 'gerado_em': agora.strftime('%Y-%m-%dT%H:%M'), 'periodo': periodo,
                 'notas': {'campanhas': d.get('nota_campanhas', ''), 'conversoes': d.get('nota_conversoes', '')}}
        nome_token = d.get('meta_token') or 'META_TOKEN'
        token = os.environ.get(nome_token, '').strip() or geral
        algum_token = algum_token or bool(token)
        try:
            if not token:
                raise RuntimeError(nome_token + ' não configurado')
            saida['meta'] = coletar_meta(d, periodo, token)
        except Exception as e:
            falhas += 1
            saida['meta'] = {'erro': str(e)[:300]}
            print('Meta falhou em %s: %s' % (d['slug'], str(e)[:200]), file=sys.stderr)
        saida['google'] = juntar_google(d, google)
        pasta = os.path.join(site, d['slug'])
        os.makedirs(pasta)
        json.dump(saida, open(os.path.join(pasta, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        open(os.path.join(pasta, 'index.html'), 'w', encoding='utf-8').write(modelo.replace('{{NOME}}', d['nome']))
        itens.append('<a class="hb-item" href="%s/"><span>%s</span><b>Abrir</b></a>' % (d['slug'], d['nome']))
        print('ok', d['slug'])
    open(os.path.join(site, 'index.html'), 'w', encoding='utf-8').write(hub.replace('{{ITENS}}', '\n'.join(itens)))
    open(os.path.join(site, '.nojekyll'), 'w').close()
    if falhas == len(cfg['dashes']) and algum_token:
        sys.exit('O Meta falhou em todos os dashes.')


if __name__ == '__main__':
    main()
