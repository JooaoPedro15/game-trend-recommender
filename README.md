# Game Trend Recommender

A local, file-based MVP that ranks games by their potential for short-form video
(YouTube Shorts, Reels, TikTok) on the Roberto Careca channel.

## Problem

Game-focused creators constantly need to decide **which game to record next**.
Catching a game while it is still rising — before it saturates — is hard to do by
hand across many channels and platforms. This tool turns manually collected video
data into a ranked, **explainable** shortlist of games worth covering.

It is an early MVP and a future building block of a larger "Creator Intelligence Platform".

## Current features

- Ranks games from manually collected video data (CSV files).
- Detects games in video titles and comments by name and aliases.
- Explainable scoring: each game shows the videos and signals behind its rank.
- Filters for `ranking` / `exportar_ranking`: platform (`--plataforma`),
  publication date (`--desde`), and top-N (`--top`).
- Report export to **Markdown** or **CSV**, timestamped under `reports/`.
- Manual video registration through the CLI, with duplicate-URL protection.
- Batch import of videos from an external CSV, with per-row validation and a summary.
- Data-quality diagnostics, plus a list of videos with no detected game.
- Alias management to grow game detection from real data.

No scraping, no external APIs, no database, no AI — **yet**. Data is filled in by hand
on purpose, to validate the ranking "brain" before automating collection.

## Tech stack

- **Python 3.10+** — standard library only at runtime (no third-party dependencies).
- **argparse** for the command-line interface.
- **pytest** for the test suite (dev-only dependency).

## Project structure

```text
game-trend-recommender/
|-- data/                      # input CSVs (filled manually)
|   |-- canais_referencia.csv
|   |-- jogos_seed.csv
|   `-- videos_coletados.csv
|-- src/
|   |-- main.py                # CLI (argparse): all commands + handlers
|   |-- ranker.py              # ranking calculation
|   |-- detector_jogo.py       # game detection by name / alias
|   |-- leitor_csv.py          # CSV reading
|   |-- cadastro_video.py      # manual + batch video registration
|   |-- cadastro_jogo.py       # add aliases to jogos_seed.csv
|   |-- diagnostico_dados.py   # data-quality diagnostics + orphan videos
|   |-- metricas_video.py      # engagement metric (single source of truth)
|   |-- relatorio.py           # Markdown / CSV report generation
|   `-- modelos.py             # dataclasses (VideoColetado, JogoSeed, ...)
|-- tests/                     # pytest suite
|-- reports/                   # generated reports (Markdown / CSV)
|-- docs/
|   |-- fluxo_dados.md
|   `-- publicacao_github.md
|-- README.md
`-- requirements.txt
```

## How to run

Requires Python 3.10+. No installation step — the runtime uses the standard library only.

```bash
python src/main.py            # defaults to "ranking"
python src/main.py ranking
```

Both read the CSVs in `data/`, detect the games mentioned in the videos, and print the
ranking ordered by final score.

## CLI commands

| Command | What it does |
|---------|--------------|
| `ranking` | Print the ranking in the terminal (default when no command is given). |
| `exportar_ranking` | Export the ranking to a timestamped file in `reports/`. |
| `adicionar_video` | Register a video manually (interactive prompts). |
| `importar_videos <csv>` | Batch-import videos from an external CSV (validates, skips duplicates and invalid rows, prints a summary). |
| `diagnosticar_dados` | Print a data-quality report of the collected videos. |
| `videos_sem_jogo` | List collected videos with no detected game, sorted by views. |
| `adicionar_alias "<jogo>" "<alias>"` | Add an alias to a game in `jogos_seed.csv` (improves detection). |

Shared options for `ranking` and `exportar_ranking`:

| Option | Description |
|--------|-------------|
| `--plataforma NAME` | Keep only videos from a platform (case-insensitive). |
| `--desde YYYY-MM-DD` | Keep only videos published on or after this date. |
| `--top N` | Show only the top N games (positive integer). |

Extra option for `exportar_ranking` only:

| Option | Description |
|--------|-------------|
| `--formato {md,csv}` | Output format (default: `md`). |

Run `python src/main.py --help` or `python src/main.py <command> --help` for the
auto-generated help.

## Example usage

```bash
# Full ranking in the terminal
python src/main.py ranking

# Top 5 YouTube games published since May 1st
python src/main.py ranking --plataforma YouTube --desde 2026-05-01 --top 5

# Export the top 10 games to CSV
python src/main.py exportar_ranking --top 10 --formato csv

# Register a video manually
python src/main.py adicionar_video

# Batch-import videos from an external CSV
python src/main.py importar_videos data/importacoes/videos_novos.csv

# Inspect data quality and find videos with no detected game
python src/main.py diagnosticar_dados
python src/main.py videos_sem_jogo

# Add an alias so a game gets detected on the next run
python src/main.py adicionar_alias "Schedule I" "schedule 1"
```

### Registering a video

`adicionar_video` prompts for: `titulo`, `canal`, `plataforma`, `url`, `views`,
`likes`, `comentarios`, `data_publicacao`, `texto_comentarios`.

Rules:
- `titulo`, `canal`, `plataforma`, `url` are required.
- `views`, `likes`, `comentarios` must be integers.
- An empty `data_publicacao` defaults to today (`YYYY-MM-DD`).
- Duplicate URLs are rejected.

## Data files

All inputs live in `data/` as CSV.

**`canais_referencia.csv`** — `nome,plataforma,url,peso`
`peso` weights channels that tend to anticipate trends or match the channel's audience.
Use `1.0` as the default.

**`jogos_seed.csv`** — `nome,aliases,genero,fit_inicial`
Separate aliases with `|` (e.g. `R.E.P.O.,repo|r.e.p.o|repo game,horror engracado,9`).
`fit_inicial` (0–10) is how well the game fits the channel before any trend data.

**`videos_coletados.csv`** — `titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios`
The detector searches names/aliases in `titulo` and `texto_comentarios`. For better
results, copy "discovery" signals from the comments, such as: `qual nome`, `que jogo`,
`what game`, `game name`, `onde baixa`, `tem na steam`, `link do jogo`.

## Ranking logic overview

```text
score_final =
    score_tendencia  * 0.40 +
    score_fit_canal  * 0.35 +
    score_descoberta * 0.15 +
    score_saturacao  * 0.10
```

- **score_tendencia** — views, likes, comments, channel weight, recency, and the number
  of distinct channels.
- **score_fit_canal** — `fit_inicial` (0–10) rescaled to 0–100.
- **score_descoberta** — higher when comments ask the game's name or where to find it.
- **score_saturacao** — favors games still seen on few channels (catch them before saturation).

The ranking also lists the videos behind each game, so you can check whether a score came
from one strong video, several channels, or curiosity in the comments.

See [`docs/fluxo_dados.md`](docs/fluxo_dados.md) for the full data flow, from input CSVs to reports.

## Testing

```bash
python -m pytest
```

`pytest` is the only development dependency; the runtime itself stays standard-library only.

## Public-repository notes

The `.gitignore` blocks caches, local environments, `.env`, secrets, and private data
folders. Keep the committed CSVs as fictional examples or data you are comfortable
publishing. For real research data, use local files such as `data/videos_coletados.local.csv`
or a `data/private/` folder that stays out of Git. See `docs/publicacao_github.md` before
pushing.

## Roadmap

- Tune the formula weights after comparing rankings with real channel results.
- Per-video CSV export (the CSV currently has one row per game).
- Automate collection (YouTube / TikTok), keeping private data separate from public examples.
- Longer term, the project may grow into scraping, a dashboard, and AI-assisted analysis.

## Project status

Early MVP under active development. Data is collected and registered **manually** — there
is no scraping or external API yet. The current focus is validating the ranking logic from
hand-filled CSVs before automating data collection, so the project is pre-1.0 and still
stabilizing.
