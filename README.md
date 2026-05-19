# Game Trend Recommender

MVP local para recomendar games com potencial para Shorts, Reels e TikTok do canal Roberto Careca.

Nesta primeira versao, o projeto nao faz scraping, nao usa APIs externas, nao usa banco de dados e nao usa IA. A ideia e testar o cerebro do ranking com arquivos CSV preenchidos manualmente.

## Como rodar

Use Python 3.10+.

```bash
python src/main.py
```

Para rodar os testes:

```bash
python -m unittest discover -s tests
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
|   |-- leitor_csv.py
|   |-- detector_jogo.py
|   |-- ranker.py
|   `-- modelos.py
|-- tests/
|   |-- test_detector_jogo.py
|   `-- test_ranker.py
|-- README.md
`-- requirements.txt
```

## Como adicionar canais

Edite `data/canais_referencia.csv`.

Colunas:

```csv
nome,plataforma,url,peso
```

O campo `peso` permite dar mais importancia para canais que historicamente antecipam tendencias ou parecem mais parecidos com o publico do Roberto Careca.

## Como adicionar jogos

Edite `data/jogos_seed.csv`.

Colunas:

```csv
nome,aliases,genero,fit_inicial
```

Use `|` para separar aliases:

```csv
R.E.P.O.,repo|r.e.p.o|repo game,horror engracado,9
```

O campo `fit_inicial` vai de 0 a 10 e representa o quanto o jogo parece combinar com o canal antes dos dados de tendencia.

## Como adicionar videos coletados manualmente

Edite `data/videos_coletados.csv`.

Colunas:

```csv
titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios
```

O detector procura nomes e aliases no `titulo` e em `texto_comentarios`. Para bons resultados, copie comentarios que indiquem curiosidade, como "qual o nome do jogo", "que jogo e esse", "onde baixa" ou "tem na steam".

## Como o ranking funciona

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

## Proximos passos

- Ajustar pesos da formula depois de comparar rankings com resultados reais do canal.
- Adicionar campos de data mais fortes para priorizar videos recentes.
- Criar uma rotina de validacao dos CSVs.
- Exportar o ranking para CSV ou Markdown.
- Em outra sprint, avaliar coleta automatica, APIs ou interface.
