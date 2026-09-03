# API FastAPI somente-leitura — design

## Objetivo

Expor os dados que hoje só existem via CLI (`src/main.py`) também por HTTP, para dois usos:
um frontend web (dashboard) e integração com sistemas externos no futuro. Esta primeira
versão é **somente leitura** e roda **só em localhost, sem autenticação**.

## Escopo v1

Endpoints somente leitura, sobre os mesmos CSVs locais que a CLI já lê. Nenhuma chamada à
API do YouTube nesta fase — só os comandos que a CLI já classifica como "offline". Escrita
(cadastrar jogo, vídeo, watchlist, disparar coleta) fica para uma fase futura.

## Arquitetura

Novo pacote `src/api/`, separado da CLI, que **reaproveita** a lógica pura já existente
(`ranker.py`, `evidencias_jogo.py`, `comparacao_meu_canal.py`, `diagnostico_dados.py`,
`repetir_jogos.py`, `jogos_falhos.py`, `historico_ranking.py`, `watchlist.py`,
`status_sistema.py`, `leitor_csv.py`, `meus_videos.py`) e os leitores de CSV — não duplica
regra de negócio, só expõe o que já existe via HTTP.

Os caminhos compartilhados (`DATA_DIR`, `VIDEOS_CSV`, `MEUS_VIDEOS_CSV`,
`HISTORICO_CSV`, `WATCHLIST_CSV`, `REPORTS_DIR`, `BASE_DIR`) saem de `src/main.py` e vão
para `src/config.py`, que passa a ser a fonte única desses caminhos. `main.py` importa de
lá em vez de redefinir; a API faz o mesmo. Isso evita duas fontes de verdade para onde os
dados moram.

```text
src/api/
  __init__.py
  main.py            # cria o FastAPI(), inclui os routers, configura CORS pra localhost
  schemas.py          # modelos Pydantic de resposta (contrato da API, separado dos dataclasses internos)
  dependencies.py       # funções de carregamento por requisição (carregar_ranking(), carregar_jogos(), ...)
  routers/
    ranking.py           # /ranking, /oportunidades
    evidencias.py          # /evidencias/{jogo}
    watchlist.py             # /watchlist, /watchlist/ranking
    meu_canal.py               # /meu-canal/sem-jogo, /comparacao, /repetir, /falhos
    diagnostico.py                # /diagnostico, /videos-sem-jogo, /descobertas-sem-jogo
    sistema.py                      # /status, /historico/comparacao
```

## Endpoints (v1)

Todos aceitam os mesmos filtros que a CLI já usa onde fizer sentido: `plataforma`,
`desde` (`YYYY-MM-DD`), `top`.

| Rota | Espelha o comando CLI |
|---|---|
| `GET /ranking` | `ranking` |
| `GET /oportunidades` | `oportunidades` |
| `GET /evidencias/{jogo}` | `evidencias_jogo` (query opcional `tipo`) |
| `GET /watchlist` | `listar_watchlist` |
| `GET /watchlist/ranking` | `ranking_watchlist` |
| `GET /diagnostico` | `diagnosticar_dados` |
| `GET /videos-sem-jogo` | `videos_sem_jogo` |
| `GET /descobertas-sem-jogo` | `descobertas_sem_jogo` |
| `GET /meu-canal/sem-jogo` | `meus_videos_sem_jogo` |
| `GET /meu-canal/comparacao` | `comparar_recomendacoes_meu_canal` |
| `GET /meu-canal/repetir` | `jogos_para_repetir` |
| `GET /meu-canal/falhos` | `jogos_que_nao_funcionaram` |
| `GET /historico/comparacao` | `comparar_rankings` |
| `GET /status` | `status_sistema` |

## Fluxo de dados

Cada requisição lê os CSVs relevantes na hora (sem cache, sem banco — mesmo modelo da
CLI), roda as mesmas funções puras e mapeia o resultado (dataclasses de `modelos.py`) para
os schemas Pydantic de `schemas.py`. Essa camada de schema é o contrato externo: internamente
os dataclasses podem mudar sem quebrar quem consome a API, desde que o schema não mude.

## Tratamento de erros

- CSV ausente → mesmo comportamento da CLI hoje: `leitor_csv` trata arquivo ausente como
  lista vazia, então a rota responde `200` com resultado vazio (ex.: ranking `[]`), não erro.
- CSV presente mas ilegível (erro de permissão/encoding ao abrir o arquivo) → `503` com
  mensagem clara.
- Jogo não encontrado em `/evidencias/{jogo}` → `404`.
- Histórico insuficiente em `/historico/comparacao` (menos de 2 snapshots) → `409` com
  mensagem explicando o motivo (mesma regra da CLI).
- Parâmetros de query inválidos (`--desde` malformado, `--top` negativo) → `422`,
  validação automática do Pydantic/FastAPI.

## Execução local

Roda em `127.0.0.1`, CORS liberado para origens `localhost` (frontend de desenvolvimento).
Sem autenticação nesta fase — nota para quando for expor além de localhost: adicionar
chave de API por header antes disso.

## Dependências novas

`fastapi` e `uvicorn` entram em `requirements.txt` como as primeiras dependências de
terceiros em tempo de execução (hoje o runtime é stdlib-only). O README ganha uma nota
sobre essa exceção pontual para a camada de API opcional.

## Testes

`tests/test_api_*.py` usando o `TestClient` do FastAPI, reaproveitando os mesmos CSVs de
fixture que os testes da CLI já usam. Cobre: caminho feliz de cada rota, filtros
(`plataforma`/`desde`/`top`), e os casos de erro acima (404/409/422/503).

## Fora de escopo (fases futuras)

- Endpoints de escrita (cadastrar jogo/vídeo/watchlist, disparar coleta do YouTube).
- Autenticação / exposição fora de localhost.
- Cache ou banco de dados — mantém o modelo atual de leitura direta dos CSVs.
