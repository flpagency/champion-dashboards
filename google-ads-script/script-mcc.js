/**
 * Champion · Google Ads para os dashes do GitHub
 *
 * Onde colar: Google Ads da MCC "Felipe Costa" (310-237-5772) > Ferramentas > Ações em massa > Scripts > botão +.
 * Frequência: de hora em hora.
 *
 * O que faz: lê o mês atual e o período anterior (os mesmos dias antes do dia 1º) de cada conta
 * e grava tudo no arquivo data/google.json do repositório no GitHub. A automação do GitHub
 * junta esses números aos do Meta e atualiza os dashes.
 *
 * Só lê o Google Ads: não muda campanha, lance nem orçamento.
 * Antes de rodar, preencha GITHUB.dono e GITHUB.token logo abaixo.
 */

var GITHUB = {
  dono: 'flpagency',                      // o nome de usuário dono do repositório
  repositorio: 'champion-dashboards',
  token: 'COLE_AQUI_O_TOKEN_DO_GITHUB',   // token "fine-grained" só deste repositório, com Contents: Read and write
  arquivo: 'data/google.json',
  ramo: 'main'
};

var CONTAS = [
  {nome: 'Champion Peugeot', id: '635-169-2539'},
  {nome: 'Champion Leapmotor DF', id: '224-192-5535'},
  {nome: 'Champion Citroën', id: '557-368-0197'},
  {nome: 'Champion Volvo DF', id: '423-847-2749'},
  {nome: 'Champion Volvo GO', id: '229-067-5049'}
];

function main() {
  var saida = {atualizado: Utilities.formatDate(new Date(), 'America/Sao_Paulo', "yyyy-MM-dd'T'HH:mm"), contas: {}};
  var contas = AdsManagerApp.accounts().withIds(CONTAS.map(function (c) { return c.id; })).get();
  while (contas.hasNext()) {
    var conta = contas.next();
    var cfg = CONTAS.filter(function (c) { return c.id === conta.getCustomerId(); })[0];
    if (!cfg) continue;
    AdsManagerApp.select(conta);
    saida.contas[cfg.id] = coletar(cfg);
    Logger.log('Lido: ' + cfg.nome);
  }
  enviar(JSON.stringify(saida));
  Logger.log('Enviado para o GitHub.');
}

function coletar(cfg) {
  var fuso = AdsApp.currentAccount().getTimeZone();
  var hoje = Utilities.formatDate(new Date(), fuso, 'yyyy-MM-dd');
  var inicio = hoje.substring(0, 8) + '01';
  var dias = Number(hoje.substring(8, 10));
  var inicioAnterior = somarDias(inicio, -dias);

  var porDia = {};
  var linhas = AdsApp.search(
    "SELECT segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions " +
    "FROM customer WHERE segments.date BETWEEN '" + inicioAnterior + "' AND '" + hoje + "'");
  while (linhas.hasNext()) {
    var r = linhas.next();
    porDia[r.segments.date] = r.metrics || {};
  }
  var diario = [];
  for (var d = inicioAnterior; d <= hoje; d = somarDias(d, 1)) {
    var m = porDia[d] || {};
    diario.push({data: d, periodo: d >= inicio ? 'atual' : 'anterior', gasto: dinheiro(m.costMicros),
                 impressoes: inteiro(m.impressions), cliques: inteiro(m.clicks), conversoes: decimal(m.conversions)});
  }

  var status = {ENABLED: 'Ativo', PAUSED: 'Inativo', REMOVED: 'Removido'};
  var campanhas = [];
  var lc = AdsApp.search(
    "SELECT campaign.id, campaign.name, campaign.status, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions " +
    "FROM campaign WHERE segments.date BETWEEN '" + inicio + "' AND '" + hoje + "' AND metrics.impressions > 0 ORDER BY metrics.cost_micros DESC");
  while (lc.hasNext()) {
    var c = lc.next();
    var mc = c.metrics || {};
    campanhas.push({id: String(c.campaign.id), campanha: c.campaign.name, status: status[c.campaign.status] || c.campaign.status,
                    gasto: dinheiro(mc.costMicros), impressoes: inteiro(mc.impressions), cliques: inteiro(mc.clicks), conversoes: decimal(mc.conversions)});
  }
  return {nome: cfg.nome, diario: diario, campanhas: campanhas};
}

function enviar(texto) {
  var url = 'https://api.github.com/repos/' + GITHUB.dono + '/' + GITHUB.repositorio + '/contents/' + GITHUB.arquivo;
  var cabecalho = {Authorization: 'Bearer ' + GITHUB.token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};
  var atual = UrlFetchApp.fetch(url + '?ref=' + GITHUB.ramo, {headers: cabecalho, muteHttpExceptions: true});
  var corpo = {message: 'Atualiza dados do Google Ads', content: Utilities.base64Encode(texto, Utilities.Charset.UTF_8), branch: GITHUB.ramo};
  if (atual.getResponseCode() === 200) corpo.sha = JSON.parse(atual.getContentText()).sha;
  var resp = UrlFetchApp.fetch(url, {method: 'put', headers: cabecalho, contentType: 'application/json', payload: JSON.stringify(corpo), muteHttpExceptions: true});
  if (resp.getResponseCode() >= 300) {
    throw new Error('O GitHub recusou o envio (' + resp.getResponseCode() + '): ' + resp.getContentText().substring(0, 300));
  }
}

function somarDias(data, n) {
  var d = new Date(Date.UTC(Number(data.substring(0, 4)), Number(data.substring(5, 7)) - 1, Number(data.substring(8, 10)) + n));
  return d.toISOString().substring(0, 10);
}
function dinheiro(micros) { return Math.round(Number(micros || 0) / 10000) / 100; }
function inteiro(v) { return Math.round(Number(v || 0)); }
function decimal(v) { return Math.round(Number(v || 0) * 100) / 100; }
