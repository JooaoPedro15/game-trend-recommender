# Fluxo de Dados

Como os dados entram, são validados, viram ranking e saem como relatório — a
visão geral do "cérebro" do Game Trend Recommender na Sprint 2.

> **Escopo da Sprint 2:** sem API, sem scraping. Os dados são **manuais**
> (cadastro pelo terminal) ou **semi-manuais** (importação de um CSV que você
> montou/exportou por fora). A meta é validar a lógica de ranking sobre dados
> preenchidos à mão **antes** de automatizar a coleta.

## Visão geral

```text
data/*.csv (manuais)                comandos de entrada
  jogos_seed.csv                      adicionar_video   (manual, 1 a 1)
  canais_referencia.csv               importar_videos   (lote, semi-manual)
  videos_coletados.csv                adicionar_alias   (ajusta a deteccao)
        |
        v
  leitor_csv  ->  detector_jogo  ->  ranker  ->  saida
  (le/valida)     (acha o jogo)      (score)     |- terminal: ranking
        |                                        '- arquivo: reports/*.md | *.csv
        v
  diagnosticar_dados / videos_sem_jogo   (qualidade + feedback para aliases)
```

## 1. Entradas (`data/*.csv`)

**`jogos_seed.csv`** — `nome,aliases,genero,fit_inicial`
A "semente" de jogos que o sistema sabe procurar. `aliases` separados por `|`
(ex: `R.E.P.O.,repo|r.e.p.o,horror,9`). `fit_inicial` (0–10) é o quanto o jogo
combina com o canal antes de qualquer dado de tendência.

**`canais_referencia.csv`** — `nome,plataforma,url,peso`
Canais de referência. `peso` (padrão `1.0`) dá mais importância a canais que
costumam antecipar tendências ou batem com o público do canal.

**`videos_coletados.csv`** — `titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios`
Os vídeos observados. `titulo` e `texto_comentarios` são onde o detector procura
nomes/aliases. Sinais de curiosidade nos comentários ("qual o nome?") alimentam o
score de descoberta.

## 2. Entrada de dados (manual e semi-manual)

- **`adicionar_video`** — cadastro interativo, um vídeo por vez. Valida campos
  obrigatórios (`titulo`, `canal`, `plataforma`, `url`) e bloqueia URL duplicada.
- **`importar_videos <csv>`** — importação em lote de um CSV externo (mesmas
  colunas). Por linha: valida → ignora duplicado por URL → grava. Uma linha
  inválida **não** aborta o lote; no fim mostra `importados / duplicados / inválidos`.
- **`adicionar_alias "Jogo" "alias"`** — adiciona um alias a um jogo do
  `jogos_seed.csv` para melhorar a detecção (não duplica, preserva o resto do arquivo).

## 3. Validação e leitura (`leitor_csv`)

`leitor_csv` lê cada CSV, normaliza (`strip`), converte números (views/likes/
comentarios → `int`; peso/fit_inicial → `float`) e devolve dataclasses
(`JogoSeed`, `CanalReferencia`, `VideoColetado`). Arquivo vazio ou ausente →
lista vazia (não quebra).

## 4. Diagnóstico de qualidade (feedback)

Antes de confiar no ranking, dá para inspecionar os dados:

- **`diagnosticar_dados`** — total de vídeos, contagem por plataforma e por canal,
  vídeos sem data, com views zeradas, sem URL, sem jogo detectado, e os jogos
  detectados com suas quantidades.
- **`videos_sem_jogo`** — vídeos órfãos (nenhum jogo detectado), ordenados por
  views. Fecha o loop de melhoria: achar o termo que o público usa →
  `adicionar_alias` → rodar de novo e o vídeo passa a ser detectado.

## 5. Detecção de jogos (`detector_jogo`)

Para cada vídeo, procura o `nome` + os `aliases` de cada jogo em
`titulo + texto_comentarios`. O texto é normalizado: acentos removidos, `casefold`
e match com **fronteira de palavra** (regex), para não casar pedaço de palavra.
Um vídeo pode casar com mais de um jogo.

## 6. Cálculo do ranking (`ranker`)

Agrupa os vídeos por jogo detectado e calcula 4 sub-scores (0–100):

```text
score_final = tendencia*0.40 + fit_canal*0.35 + descoberta*0.15 + saturacao*0.10
```

- **tendencia** — views, likes, comentários, taxa de engajamento, peso do canal,
  recência (`data_publicacao`) e número de canais distintos.
- **fit_canal** — `fit_inicial` (0–10) reescalado para 0–100.
- **descoberta** — sobe quando os comentários perguntam o nome do jogo ou onde achá-lo.
- **saturacao** — favorece jogos ainda em poucos canais (oportunidade antes de saturar).

O resultado sai ordenado por `score_final` (desc). Cada item guarda os vídeos que
influenciaram e um `motivo` em texto.

### Filtros (aplicados ANTES do cálculo)

- `--plataforma NOME` — só a plataforma informada (ignora maiúsculas).
- `--desde AAAA-MM-DD` — só vídeos publicados nessa data ou depois (data inválida é ignorada).
- `--top N` — corta nos N de maior score, **depois** de ordenar (como `LIMIT` após `ORDER BY`).

## 7. Saída

- **Terminal** (`ranking`) — por jogo: scores, motivo e os vídeos que
  influenciaram (com % de engajamento).
- **Arquivo** (`exportar_ranking --formato md|csv`) — gera
  `reports/ranking_AAAA-MM-DD_HH-MM.{md,csv}`. **Markdown** = leitura humana;
  **CSV** = uma linha por jogo (10 colunas) para planilha/análise.

## Próximos passos (fora da Sprint 2)

Automatizar a coleta (scraping de YouTube/TikTok), dashboard e análise assistida
por IA — sempre separando dados privados de exemplos públicos (ver
`docs/publicacao_github.md`).
