# Champion · dashes de mídia

Relatórios de desempenho do Meta Ads e do Google Ads das lojas Champion, no visual do Metrifiquei.
O GitHub atualiza tudo sozinho de hora em hora e publica no GitHub Pages:

- Todos: https://flpagency.github.io/champion-dashboards/
- Peugeot: https://flpagency.github.io/champion-dashboards/peugeot/
- Leapmotor: https://flpagency.github.io/champion-dashboards/leapmotor/
- Citroën: https://flpagency.github.io/champion-dashboards/citroen/
- Volvo (sem a Seminovos Premium): https://flpagency.github.io/champion-dashboards/volvo/
- Seminovos Premium (campanhas com PREMIUM na conta da Volvo): https://flpagency.github.io/champion-dashboards/seminovos-premium/
- Seminovos: https://flpagency.github.io/champion-dashboards/seminovos/

## Como funciona

- `config/dashes.json`: as contas de cada dash e o filtro de campanha (a Volvo tira o PREMIUM; a Seminovos Premium fica só com ele).
- `scripts/montar.py`: busca o Meta pela API com o token do segredo `META_TOKEN`, junta o Google de `data/google.json` e monta o site.
- `.github/workflows/atualizar.yml`: roda de hora em hora, a cada envio e pelo botão "Run workflow".
- `google-ads-script/script-mcc.js`: script da MCC do Google Ads que grava `data/google.json` no repositório de hora em hora.
- `modelo/`: as páginas (dash e lista de dashes).

O período é sempre do dia 1º até hoje, comparado aos mesmos dias antes do dia 1º.

## Configuração (uma vez)

1. **Pages:** em Settings › Pages, em "Source", escolher **GitHub Actions**.
2. **Tokens do Meta:** um usuário do sistema em cada portfólio da Champion, com acesso de leitura às contas e um token com `ads_read`. Cada token vai em Settings › Secrets and variables › Actions › New repository secret:
   - `META_TOKEN_PEUGEOT`: portfólio Champion Peugeot (contas Peugeot e Seminovos)
   - `META_TOKEN_LEAPMOTOR`: portfólio Champion Leapmotor
   - `META_TOKEN_CITROEN`: portfólio Champion Citroen
   - `META_TOKEN_VOLVO`: portfólio Champion Volvo (dashes Volvo e Seminovos Premium)
   - Um único `META_TOKEN` com acesso a todas as contas também serve, para qualquer dash sem o seu.
3. **Google Ads:** criar um token "fine-grained" do GitHub só para este repositório, com Contents: Read and write. Colar no `script-mcc.js` (campo `GITHUB.token`), colar o script em Ferramentas › Scripts da MCC 310-237-5772, autorizar, executar uma vez e programar de hora em hora.
4. **Primeira atualização:** em Actions › Atualizar dashes › Run workflow.

Os dados de anúncio ficam visíveis para quem tiver o link. Não há dado pessoal.
