# Monitoramento e Decisão

Os comandos da Fase 5 transformam o ranking de uma foto única em **acompanhamento ao
longo do tempo**. Tudo roda offline sobre os CSVs locais e nenhum altera o cálculo do
ranking — só leem, salvam e comparam.

## Fluxo recomendado

```text
coletar dados        (adicionar_video / importar_videos / coletar_*_youtube)
  -> rodar ranking   (ranking)
  -> salvar snapshot (salvar_snapshot_ranking)   # periodicamente, ex: 1x por dia
  -> comparar        (comparar_rankings)         # o que subiu/caiu desde a ultima vez
  -> decidir         (oportunidades + ranking_watchlist) -> proximos conteudos
```

A watchlist (`adicionar_watchlist`) corre em paralelo: marca jogos que você quer seguir
independente da posição de hoje.

## Histórico

### `salvar_snapshot_ranking [--plataforma] [--desde] [--top]`
Calcula o ranking atual e **acrescenta** uma linha por jogo a
`data/historico_rankings.csv`, carimbada com data e hora. É **append-only**: nunca apaga
snapshots antigos, e cria o cabeçalho na primeira execução. Rode periodicamente para
montar uma série temporal.
```bash
python src/main.py salvar_snapshot_ranking
python src/main.py salvar_snapshot_ranking --plataforma YouTube --top 10
```

### `comparar_rankings`
Pega as **duas execuções mais recentes** do histórico e mostra, por jogo: quem **subiu**
de posição, quem **caiu**, quem é **novo**, quem **sumiu**, com a variação de
`score_final` e `score_oportunidade`. Precisa de pelo menos duas execuções salvas (senão
avisa que o histórico é insuficiente).
```bash
python src/main.py comparar_rankings
```
Leitura rápida:
- **subiu + oportunidade subindo** = acelerando, a melhor hora de gravar;
- **caiu + oportunidade caindo** = janela fechando;
- **novo** = sinal precoce, vale investigar;
- **sumiu** = saiu do recorte.

Subir de posição com o score *caindo* acontece (o rival caiu mais) — por isso os deltas
aparecem junto da posição; leia os dois.

## Oportunidades

### `oportunidades [--plataforma] [--desde] [--top]`
Filtra o ranking e mostra só os jogos com **alto potencial de oportunidade**, preservando
a posição original de cada um. Critérios (heurísticos do MVP, calibráveis depois), todos
exigidos juntos: `score_oportunidade >= 70`, `score_final >= 60`, `score_saturacao >= 55`,
`videos_encontrados >= 1`. A ideia é uma shortlist curta e confiável, não uma lista longa.
```bash
python src/main.py oportunidades --desde 2026-06-01
```

## Watchlist

Lista pessoal de jogos a acompanhar de perto, em `data/watchlist_jogos.csv`. O dedup
ignora maiúsculas/minúsculas.

| Comando | O que faz |
|---|---|
| `adicionar_watchlist "<jogo>"` | adiciona um jogo à lista |
| `listar_watchlist` | lista os jogos marcados |
| `remover_watchlist "<jogo>"` | remove um jogo da lista |
| `ranking_watchlist [--plataforma] [--desde] [--top]` | mostra como cada jogo da watchlist aparece no ranking atual (posição, score final, oportunidade, ação, motivo — ou "não aparece") |

```bash
python src/main.py adicionar_watchlist "R.E.P.O."
python src/main.py ranking_watchlist
```
> O cruzamento é por **nome exato** (ignorando maiúsculas). Cadastre o jogo na watchlist
> com o mesmo nome usado no `jogos_seed.csv` (ex: `"R.E.P.O."`, não `"repo"`), senão ele
> aparece como "não aparece" mesmo estando no ranking.

## Arquivos gerados (fora do Git)

`data/historico_rankings.csv` e `data/watchlist_jogos.csv` são dados **gerados e pessoais**
— estão no `.gitignore`, não vão para o repositório público.
