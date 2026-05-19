# Game Trend Recommender

MVP local para recomendar games com potencial para Shorts, Reels e TikTok do canal Roberto Careca.

Nesta versao, o projeto nao faz scraping, nao usa APIs externas, nao usa banco de dados e nao usa IA. A ideia e testar o cerebro do ranking com arquivos CSV preenchidos manualmente.

## Como rodar o ranking

Use Python 3.10+.

```bash
python src/main.py
```

Ou:

```bash
python src/main.py ranking
```

Os dois comandos leem os CSVs em `data/`, detectam os jogos citados nos videos e mostram o ranking ordenado por score final.

## Como cadastrar video manualmente

Use:

```bash
python src/main.py adicionar_video
```

O terminal vai pedir:

- `titulo`
- `canal`
- `plataforma`
- `url`
- `views`
- `likes`
- `comentarios`
- `data_publicacao`
- `texto_comentarios`

Regras do cadastro:

- `titulo`, `canal`, `plataforma` e `url` sao obrigatorios.
- `views`, `likes` e `comentarios` devem ser numeros inteiros.
- Se `data_publicacao` ficar vazia, o sistema usa a data atual no formato `YYYY-MM-DD`.
- O sistema nao permite cadastrar duas linhas com a mesma URL.

## Como rodar os testes

```bash
python -m unittest discover tests
```

## Estrutura

```text
game-trend-recommender/
|-- data/
|   |-- canais_referencia.csv
|   |-- jogos_seed.csv
|   `-- videos_coletados.csv
|-- src/
|   |-- main.py
|   |-- cadastro_video.py
|   |-- leitor_csv.py
|   |-- detector_jogo.py
|   |-- ranker.py
|   `-- modelos.py
|-- tests/
|   |-- test_cadastro_video.py
|   |-- test_detector_jogo.py
|   `-- test_ranker.py
|-- docs/
|   `-- publicacao_github.md
|-- README.md
`-- requirements.txt
```

## Como preencher canais_referencia.csv

Arquivo: `data/canais_referencia.csv`

Colunas:

```csv
nome,plataforma,url,peso
```

Exemplo:

```csv
Canal Referencia 1,youtube,https://youtube.com/@canal1,1.0
Canal Referencia 2,tiktok,https://tiktok.com/@canal2,1.2
```

O campo `peso` permite dar mais importancia para canais que historicamente antecipam tendencias ou parecem mais parecidos com o publico do Roberto Careca. Use `1.0` como padrao.

## Como preencher jogos_seed.csv

Arquivo: `data/jogos_seed.csv`

Colunas:

```csv
nome,aliases,genero,fit_inicial
```

Use `|` para separar aliases:

```csv
R.E.P.O.,repo|r.e.p.o|repo game,horror engracado,9
```

O campo `fit_inicial` vai de 0 a 10 e representa o quanto o jogo parece combinar com o canal antes dos dados de tendencia.

## Como preencher videos_coletados.csv

Arquivo: `data/videos_coletados.csv`

Colunas:

```csv
titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios
```

O detector procura nomes e aliases no `titulo` e em `texto_comentarios`. Para bons resultados, copie sinais de curiosidade dos comentarios, como:

- `qual nome`
- `nome?`
- `que jogo`
- `what game`
- `game name`
- `onde baixa`
- `tem na steam`
- `link do jogo`

## Como interpretar o score

A formula inicial e:

```text
score_final =
score_tendencia * 0.40 +
score_fit_canal * 0.35 +
score_descoberta * 0.15 +
score_saturacao * 0.10
```

- `score_tendencia`: considera views, likes, comentarios, peso do canal e quantidade de canais diferentes.
- `score_fit_canal`: transforma `fit_inicial` de 0-10 para 0-100.
- `score_descoberta`: aumenta quando comentarios perguntam o nome do jogo ou onde encontrar.
- `score_saturacao`: favorece jogos que ainda aparecem em poucos canais, para tentar capturar oportunidades antes de saturarem.

O ranking tambem mostra os videos que influenciaram cada jogo. Isso ajuda a conferir se o score veio de um video forte, de varios canais ou de comentarios de curiosidade.

## Cuidados para repositorio publico

Este projeto tem um `.gitignore` preparado para bloquear caches, ambientes locais, arquivos `.env`, segredos e pastas de dados privados.

Mantenha os CSVs versionados como exemplos ficticios ou dados que voce aceita publicar. Para dados reais de pesquisa, use arquivos locais como `data/videos_coletados.local.csv` ou pastas como `data/private/`, que nao devem subir para o GitHub.

Veja o checklist em `docs/publicacao_github.md` antes de fazer push.

## Proximos passos

- Ajustar pesos da formula depois de comparar rankings com resultados reais do canal.
- Melhorar o peso de recencia usando `data_publicacao`.
- Exportar o ranking para CSV ou Markdown.
- Sprint 2: automatizar coleta do YouTube, ainda com cuidado para separar dados privados dos exemplos publicos.
