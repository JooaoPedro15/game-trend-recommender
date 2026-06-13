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
- Explainable scoring: each game shows the videos and signals behind its rank, plus an
  **opportunity score**, a human-readable reason and a **recommended action**.
- Filters for `ranking` / `exportar_ranking`: platform (`--plataforma`),
  publication date (`--desde`), and top-N (`--top`).
- Report export to **Markdown** or **CSV**, timestamped under `reports/`.
- Manual video registration through the CLI, with duplicate-URL protection.
- Batch import of videos from an external CSV, with per-row validation and a summary.
- Data-quality diagnostics, plus a list of videos with no detected game.
- Alias management to grow game detection from real data.
- Monitoring tools: ranking history snapshots, snapshot comparison (rose/fell/new/gone),
  an opportunity shortlist and a personal watchlist — see [`docs/monitoring.md`](docs/monitoring.md).
- **Optional:** collect videos from YouTube (Data API v3) — by video id, in batch from an
  id file, or a channel's recent uploads — with a local cache to save API quota.

No scraping, no database, no AI yet. The only network features are the optional YouTube
collectors above; everything else runs offline from local CSVs.

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
|   |-- coletor_youtube.py     # YouTube Data API v3 collector (optional)
|   |-- config.py              # reads YOUTUBE_API_KEY from the environment
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
| `coletar_video_youtube <video_id>` | Fetch one video from YouTube by id and save it to the CSV (**needs `YOUTUBE_API_KEY`**). |
| `coletar_videos_youtube <ids.txt>` | Batch-fetch YouTube videos from a file with one video id per line (**needs `YOUTUBE_API_KEY`**). |
| `coletar_canal_youtube <channel_id> [--limite N]` | Fetch a channel's recent uploads (default 5) and save them (**needs `YOUTUBE_API_KEY`**). |
| `oportunidades` | List only the games with high opportunity potential (a filtered shortlist). |
| `salvar_snapshot_ranking` | Append the current ranking to a timestamped history CSV. |
| `comparar_rankings` | Compare the two most recent saved snapshots (who rose, fell, is new or gone). |
| `adicionar_watchlist "<jogo>"` | Add a game to your personal watchlist. |
| `listar_watchlist` | List the games on the watchlist. |
| `remover_watchlist "<jogo>"` | Remove a game from the watchlist. |
| `ranking_watchlist` | Show how each watchlist game ranks right now. |

See [`docs/monitoring.md`](docs/monitoring.md) for the history / comparison / watchlist
workflow and the recommended routine.

Shared options for `ranking`, `exportar_ranking`, `oportunidades`,
`salvar_snapshot_ranking` and `ranking_watchlist`:

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

## YouTube Data API (optional)

Only the YouTube collectors (`coletar_video_youtube`, `coletar_videos_youtube`,
`coletar_canal_youtube`) touch the network. Everything else — ranking, history,
watchlist, CSV import, diagnostics, alias management and report export — works fully
offline from the local CSVs, with **no API key**.

**Setup:**

1. In the Google Cloud Console, enable **YouTube Data API v3** and create an **API key**.
2. Put the key in the `YOUTUBE_API_KEY` environment variable (never in code).
3. Run the collector.

```bash
export YOUTUBE_API_KEY=your_key            # bash / zsh
# PowerShell:  $env:YOUTUBE_API_KEY = "your_key"
python src/main.py coletar_video_youtube dQw4w9WgXcQ
```

The fetch reads title, channel, url, views, likes, comments and publication date,
converts them to the same `VideoColetado` format, and appends to
`data/videos_coletados.csv` (duplicate URLs are rejected). From there the video flows
through the normal ranking pipeline. It fetches **one video by id** — not channels or
bulk collection (those are future work).

**Key safety:**

- `.env.example` documents only the **name** (`YOUTUBE_API_KEY=`) — **never** a real key.
- Put the real value in `.env` / `.env.local`, which are gitignored.
- The code only reads the key from the environment; it is never written into source.
- `.env` is **not auto-loaded** — export the variable in your shell. (Auto-loading `.env`
  would need an extra dependency, which has not been added.)
- Quota: the free tier is ~10,000 units/day; one video fetch costs 1 unit.

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

# Fetch one video from YouTube by id and save it (needs YOUTUBE_API_KEY)
python src/main.py coletar_video_youtube dQw4w9WgXcQ
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

- **score_tendencia** — views, likes, comments, **engagement rate**, **velocity
  (views/day)**, a per-platform weight (autoplay views count slightly less than
  YouTube views), channel weight and recency.
- **score_fit_canal** — `fit_inicial` (0–10) rescaled to 0–100.
- **score_descoberta** — higher when comments ask the game's name or where to find it.
- **score_saturacao** — favors games still seen on few channels (catch them before saturation).

On top of those, each game also gets:

- **score_oportunidade** = `tendencia*0.40 + saturacao*0.40 + descoberta*0.20` — "where is
  the entry window?" (fit is excluded on purpose: the opportunity belongs to the market).
- a **reason** in plain language, aware of the opportunity signals;
- a **recommended action** (prioritize a long video, test in a Short, research more,
  monitor, or avoid due to saturation).

All weights and thresholds are **MVP heuristics** — chosen deliberately but not yet
calibrated against real channel results (that tuning is on the roadmap). See
[`docs/ranking_logic.md`](docs/ranking_logic.md) for every formula and threshold, and
[`docs/fluxo_dados.md`](docs/fluxo_dados.md) for the full data flow.

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

Early MVP under active development. Data is mostly manual — CSV import and manual entry —
plus optional YouTube collection (single video, id batch, or a channel's recent uploads).
No scraping, dashboard or AI yet. The ranking weights are uncalibrated heuristics, so the
project is pre-1.0 and stabilizing.
