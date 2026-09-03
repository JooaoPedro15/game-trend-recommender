# API FastAPI somente-leitura — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expor os dados do Game Trend Recommender (ranking, evidências, watchlist, diagnóstico, meu canal, status) via uma API FastAPI somente-leitura, local, sem autenticação, reaproveitando 100% da lógica pura já existente.

**Architecture:** Extrai duas peças de lógica hoje presas em `main.py` (montagem/filtro do ranking, caminhos de dados) para módulos compartilhados (`ranking_service.py`, `config.py`), depois adiciona um pacote `src/api/` com routers FastAPI finos que só leem CSV, chamam funções puras existentes e mapeiam o resultado para schemas Pydantic.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2, `httpx` (para o `TestClient` nos testes), `unittest`/`pytest` (padrão já usado no projeto).

**Spec:** `docs/superpowers/specs/2026-09-03-fastapi-somente-leitura-design.md`

---

## Antes de começar

Todos os comandos assumem `cwd` = raiz do projeto (`D:\Projetos\game-trend-recommender`) e `python` = o interpretador que já roda a suíte hoje (confirmado: `py -3.14`, 393 testes passando). Ajuste o comando de teste se o seu ambiente usar outro alias.

```bash
py -3.14 -m pytest -q
```

Rode isso agora, antes do Task 1, para confirmar a baseline verde.

---

### Task 1: Extrair `ranking_service.py` (monta/filtra o ranking)

Hoje `_filtrar_por_plataforma`, `_filtrar_por_data` e `_montar_ranking` vivem só em `src/main.py` (linhas ~278-294 e ~1698-1715) e são importadas diretamente pelos testes (`tests/test_filtros.py`). Vamos mover a implementação para um módulo novo e deixar `main.py` com finas funções de compatibilidade (mesmo nome, mesmo comportamento) para não quebrar `test_filtros.py`. Isso dá à API um jeito de montar o ranking sem importar `main.py` (que faz parsing de CLI).

**Files:**
- Create: `src/ranking_service.py`
- Test: `tests/test_ranking_service.py`
- Modify: `src/main.py` (linhas 264-294 e 1698-1715 — ver abaixo)

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_ranking_service.py`:

```python
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, VideoColetado
from ranking_service import carregar_ranking, filtrar_por_data, filtrar_por_plataforma, montar_ranking


def _video(plataforma="youtube", dias_atras=0, titulo="Video"):
    data = (date.today() - timedelta(days=dias_atras)).isoformat()
    return VideoColetado(
        titulo=titulo, canal="Canal", plataforma=plataforma,
        url=f"https://y/{titulo}", views=1000, likes=10, comentarios=1,
        data_publicacao=data, texto_comentarios="",
    )


def test_filtrar_por_plataforma_ignora_maiusculas():
    videos = [_video(plataforma="YouTube"), _video(plataforma="TikTok")]
    filtrados = filtrar_por_plataforma(videos, "youtube")
    assert len(filtrados) == 1
    assert filtrados[0].plataforma == "YouTube"


def test_filtrar_por_data_mantem_so_a_partir_da_data():
    videos = [_video(dias_atras=1), _video(dias_atras=10)]
    filtrados = filtrar_por_data(videos, date.today() - timedelta(days=5))
    assert len(filtrados) == 1


def test_montar_ranking_aplica_top():
    jogos = [
        JogoSeed(nome="Jogo A", aliases=["jogo a"], genero="", fit_inicial=5),
        JogoSeed(nome="Jogo B", aliases=["jogo b"], genero="", fit_inicial=5),
    ]
    videos = [_video(titulo="jogo a"), _video(titulo="jogo b")]
    ranking = montar_ranking(jogos, videos, [], top=1)
    assert len(ranking) == 1


def test_carregar_ranking_le_csvs_do_diretorio(tmp_path):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,1000,10,1,2026-05-01,\n",
        encoding="utf-8",
    )
    meus_videos_csv = tmp_path / "meus_videos.csv"

    ranking = carregar_ranking(tmp_path, videos_csv, meus_videos_csv)

    assert len(ranking) == 1
    assert ranking[0].jogo.nome == "Repo"
```

- [ ] **Step 2: Rodar e confirmar que falha (módulo não existe)**

Run: `py -3.14 -m pytest tests/test_ranking_service.py -v`
Expected: `ModuleNotFoundError: No module named 'ranking_service'`

- [ ] **Step 3: Criar `src/ranking_service.py`**

```python
# Monta e filtra o ranking a partir dos CSVs. Extraido de main.py para ser reusado
# tanto pela CLI quanto pela API, sem nenhuma das duas depender da outra.

from datetime import date
from pathlib import Path

from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from meus_videos import ler_meus_videos
from modelos import VideoColetado
from ranker import calcular_ranking


def filtrar_por_plataforma(videos: list[VideoColetado], plataforma: str) -> list[VideoColetado]:
    plataforma_alvo = plataforma.casefold()
    return [video for video in videos if video.plataforma.casefold() == plataforma_alvo]


def filtrar_por_data(videos: list[VideoColetado], desde: date) -> list[VideoColetado]:
    selecionados = []
    for video in videos:
        try:
            data_video = date.fromisoformat(video.data_publicacao)
        except ValueError:
            continue
        if data_video >= desde:
            selecionados.append(video)
    return selecionados


# Aplica os filtros de plataforma e data e o limite Top N (se houver) e retorna o ranking.
# Os filtros incidem so nos videos de referencia; o fit real usa todo o historico do canal.
def montar_ranking(
    jogos,
    videos,
    canais,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
    meus_videos=None,
):
    if plataforma:
        videos = filtrar_por_plataforma(videos, plataforma)
    if desde is not None:
        videos = filtrar_por_data(videos, desde)
    ranking = calcular_ranking(jogos, videos, canais, meus_videos)
    if top is not None:
        ranking = ranking[:top]
    return ranking


# Le os CSVs do diretorio dado e monta o ranking. data_dir aponta para a pasta com
# jogos_seed.csv e canais_referencia.csv; videos_csv e meus_videos_csv sao caminhos
# explicitos porque a CLI e a API podem apontar para arquivos com nomes diferentes.
def carregar_ranking(
    data_dir: str | Path,
    videos_csv: str | Path,
    meus_videos_csv: str | Path,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
):
    data_dir = Path(data_dir)
    canais = ler_canais_referencia(data_dir / "canais_referencia.csv")
    jogos = ler_jogos_seed(data_dir / "jogos_seed.csv")
    videos = ler_videos_coletados(videos_csv)
    meus_videos = ler_meus_videos(meus_videos_csv)
    return montar_ranking(jogos, videos, canais, plataforma, top, desde, meus_videos)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_ranking_service.py -v`
Expected: 4 passed

- [ ] **Step 5: Apontar `main.py` para o novo módulo (mantendo os nomes antigos)**

Em `src/main.py`, adicione o import (perto dos outros imports locais, por exemplo depois da linha `from ranker import calcular_ranking, filtrar_oportunidades`):

```python
import ranking_service
```

Substitua o corpo de `_carregar_ranking` (linhas 266-273) por:

```python
def _carregar_ranking(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
):
    return ranking_service.carregar_ranking(
        DATA_DIR, VIDEOS_CSV, MEUS_VIDEOS_CSV, plataforma, top, desde
    )
```

Substitua o corpo de `_montar_ranking` (linhas 278-294) por:

```python
def _montar_ranking(
    jogos,
    videos,
    canais,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
    meus_videos=None,
):
    return ranking_service.montar_ranking(jogos, videos, canais, plataforma, top, desde, meus_videos)
```

Substitua `_filtrar_por_plataforma` e `_filtrar_por_data` (linhas ~1698-1715) por:

```python
_filtrar_por_plataforma = ranking_service.filtrar_por_plataforma
_filtrar_por_data = ranking_service.filtrar_por_data
```

- [ ] **Step 6: Rodar a suíte inteira**

Run: `py -3.14 -m pytest -q`
Expected: `397 passed` (393 + 4 novos)

- [ ] **Step 7: Commit**

```bash
git add src/ranking_service.py tests/test_ranking_service.py src/main.py
git commit -m "refatora: extrai montagem do ranking para ranking_service.py"
```

---

### Task 2: Mover caminhos de dados compartilhados para `config.py`

`DATA_DIR`, `VIDEOS_CSV`, `MEUS_VIDEOS_CSV`, `HISTORICO_CSV`, `WATCHLIST_CSV` e `REPORTS_DIR` (hoje só em `main.py:74-82`) precisam existir num lugar que a API também importe, sem puxar o parser de CLI.

**Files:**
- Modify: `src/config.py`
- Modify: `src/main.py:74-82`
- Test: `tests/test_config.py` (já existe — só adiciona casos novos)

- [ ] **Step 1: Ver o teste atual para seguir o padrão**

Leia `tests/test_config.py` antes de editar, para manter o estilo dos testes existentes.

- [ ] **Step 2: Escrever o teste que falha**

Adicione ao fim de `tests/test_config.py`:

```python
def test_caminhos_de_dados_existem_e_sao_consistentes():
    import config

    assert config.DATA_DIR == config.BASE_DIR / "data"
    assert config.VIDEOS_CSV == config.DATA_DIR / "videos_coletados.csv"
    assert config.MEUS_VIDEOS_CSV == config.DATA_DIR / "meus_videos.csv"
    assert config.HISTORICO_CSV == config.DATA_DIR / "historico_rankings.csv"
    assert config.WATCHLIST_CSV == config.DATA_DIR / "watchlist_jogos.csv"
    assert config.REPORTS_DIR == config.BASE_DIR / "reports"
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_config.py -v`
Expected: `AttributeError: module 'config' has no attribute 'DATA_DIR'`

- [ ] **Step 4: Adicionar os caminhos em `src/config.py`**

Depois da linha `ENV_PATH = BASE_DIR / ".env"` em `src/config.py`, adicione:

```python
# Caminhos de dados compartilhados entre a CLI (main.py) e a API (api/). Ficam aqui
# para nao criar duas fontes de verdade sobre onde os CSVs moram.
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
MEUS_VIDEOS_CSV = DATA_DIR / "meus_videos.csv"
HISTORICO_CSV = DATA_DIR / "historico_rankings.csv"
WATCHLIST_CSV = DATA_DIR / "watchlist_jogos.csv"
REPORTS_DIR = BASE_DIR / "reports"
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_config.py -v`
Expected: passed

- [ ] **Step 6: Apontar `main.py` para `config.py`**

Em `src/main.py`, o import de `config` já existe (linha 26-31). Adicione os nomes novos a esse import:

```python
from config import (
    DATA_DIR,
    HISTORICO_CSV,
    MEUS_VIDEOS_CSV,
    REPORTS_DIR,
    VIDEOS_CSV,
    WATCHLIST_CSV,
    ler_chave_youtube,
    ler_id_canal_proprio,
    obter_meu_canal_youtube_id,
    obter_youtube_api_key,
)
```

Remova as linhas 74-82 (as definições antigas de `BASE_DIR`, `DATA_DIR`, `VIDEOS_CSV`, `MEUS_VIDEOS_CSV`, `HISTORICO_CSV`, `WATCHLIST_CSV`, `REPORTS_DIR`), mas **mantenha** `MEU_CANAL_IDS_CHECKPOINT` e `RANKING_REPORT` (são específicos da CLI, a API não usa):

```python
BASE_DIR = Path(__file__).resolve().parents[1]
MEU_CANAL_IDS_CHECKPOINT = DATA_DIR / "meu_canal_ids_checkpoint.json"
RANKING_REPORT = REPORTS_DIR / "ranking.md"
```

(mantém `BASE_DIR` local também — é usado só para montar esses dois caminhos que ficam na CLI.)

- [ ] **Step 7: Rodar a suíte inteira**

Run: `py -3.14 -m pytest -q`
Expected: `398 passed`

- [ ] **Step 8: Commit**

```bash
git add src/config.py src/main.py tests/test_config.py
git commit -m "refatora: centraliza caminhos de dados em config.py"
```

---

### Task 3: Esqueleto do pacote `src/api/`

**Files:**
- Modify: `requirements.txt`
- Create: `src/api/__init__.py`
- Create: `src/api/main.py`
- Test: `tests/test_api_app.py`

- [ ] **Step 1: Reescrever `requirements.txt` em UTF-8 com as dependências novas**

O arquivo atual está salvo em UTF-16 (abra-o e confirme: `python -c "print(open('requirements.txt','rb').read()[:4])"` mostra um BOM `ff fe`). Reescreva-o do zero, em UTF-8, com as três linhas:

```text
python-dotenv==1.2.2
pytest==8.4.2
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
```

- [ ] **Step 2: Instalar as dependências novas**

Run: `py -3.14 -m pip install fastapi==0.115.0 "uvicorn[standard]==0.32.0" httpx==0.27.2`
Expected: instalação sem erro.

- [ ] **Step 3: Escrever o teste que falha**

Crie `tests/test_api_app.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from api.main import app


def test_app_sobe_e_expoe_openapi():
    client = TestClient(app)
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
```

- [ ] **Step 4: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_app.py -v`
Expected: `ModuleNotFoundError: No module named 'api'`

- [ ] **Step 5: Criar `src/api/__init__.py`** (vazio)

- [ ] **Step 6: Criar `src/api/main.py`**

```python
# API FastAPI somente-leitura sobre os mesmos CSVs locais que a CLI (main.py) le.
# Roda em localhost, sem autenticacao (ver docs/superpowers/specs/2026-09-03-...).

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Game Trend Recommender API",
    description="Leitura do ranking, evidencias, watchlist e status do sistema.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

- [ ] **Step 7: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_app.py -v`
Expected: passed

- [ ] **Step 8: Commit**

```bash
git add requirements.txt src/api/__init__.py src/api/main.py tests/test_api_app.py
git commit -m "feat(api): cria esqueleto do app FastAPI"
```

---

### Task 4: `schemas.py` — contratos de resposta

Define todos os modelos Pydantic usados pelos routers das próximas tasks. Sem lógica, só forma. `from_attributes=True` deixa mapear direto de um dataclass (`Schema.model_validate(objeto)`).

**Files:**
- Create: `src/api/schemas.py`
- Test: `tests/test_api_schemas.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_api_schemas.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, ResultadoRecomendacao
from api.schemas import RankingItemOut


def test_ranking_item_out_aceita_campos_manuais():
    jogo = JogoSeed(nome="Repo", aliases=["repo"], genero="terror", fit_inicial=8)
    resultado = ResultadoRecomendacao(
        jogo=jogo, score_final=80.0, score_tendencia=70.0, score_fit_canal=80.0,
        score_descoberta=10.0, score_saturacao=90.0, videos_encontrados=1,
        canais_diferentes=1, motivo="motivo", videos=[],
    )
    item = RankingItemOut(
        posicao=1, jogo=resultado.jogo.nome, score_final=resultado.score_final,
        score_tendencia=resultado.score_tendencia, score_fit_canal=resultado.score_fit_canal,
        score_fit_real=resultado.score_fit_real, formato_sugerido=resultado.formato_sugerido,
        score_descoberta=resultado.score_descoberta, score_saturacao=resultado.score_saturacao,
        score_oportunidade=resultado.score_oportunidade,
        score_evidencia_criadores=resultado.score_evidencia_criadores,
        score_evidencia_nicho=resultado.score_evidencia_nicho,
        videos_encontrados=resultado.videos_encontrados,
        canais_diferentes=resultado.canais_diferentes, motivo=resultado.motivo,
        acao_recomendada=resultado.acao_recomendada, videos=[],
    )
    assert item.jogo == "Repo"
    assert item.model_dump()["score_final"] == 80.0
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'api.schemas'`

- [ ] **Step 3: Criar `src/api/schemas.py`**

```python
# Contratos de resposta da API: separados dos dataclasses internos (modelos.py) de
# proposito, para o formato de saida poder ficar estavel mesmo se o interno mudar.

from pydantic import BaseModel, ConfigDict


class _Mirror(BaseModel):
    """Base para schemas que so espelham um dataclass 1:1 (usa from_attributes)."""
    model_config = ConfigDict(from_attributes=True)


# --- ranking / oportunidades -------------------------------------------------

class RankingVideoOut(BaseModel):
    titulo: str
    canal: str
    plataforma: str
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    taxa_engajamento: float
    views_por_dia: float


class RankingItemOut(BaseModel):
    posicao: int
    jogo: str
    score_final: float
    score_tendencia: float
    score_fit_canal: float
    score_fit_real: float | None
    formato_sugerido: str
    score_descoberta: float
    score_saturacao: float
    score_oportunidade: float
    score_evidencia_criadores: float
    score_evidencia_nicho: float
    videos_encontrados: int
    canais_diferentes: int
    motivo: str
    acao_recomendada: str
    videos: list[RankingVideoOut]


class OportunidadeOut(BaseModel):
    posicao: int
    jogo: str
    score_final: float
    score_oportunidade: float
    score_saturacao: float
    acao_recomendada: str
    motivo: str


# --- evidencias ---------------------------------------------------------------

class EvidenciaVideoOut(_Mirror):
    canal: str
    plataforma: str
    tipo_video: str
    titulo: str
    url: str
    views: int
    likes: int
    comentarios: int
    taxa_engajamento: float
    views_por_dia: float
    score_viralidade_video: float
    data_publicacao: str
    nicho: str
    tipo_conteudo: str
    peso_similaridade: float


class EvidenciasJogoOut(BaseModel):
    jogo: str
    score_evidencia: float
    resumo: str
    videos: list[EvidenciaVideoOut]


# --- watchlist ------------------------------------------------------------------

class WatchlistRankingItemOut(BaseModel):
    nome: str
    posicao: int | None
    score_final: float | None
    score_oportunidade: float | None
    acao_recomendada: str | None
    motivo: str | None


# --- diagnostico / qualidade de dados --------------------------------------------

class DiagnosticoOut(_Mirror):
    total: int
    por_plataforma: dict[str, int]
    por_canal: dict[str, int]
    por_origem: dict[str, int]
    sem_data_publicacao: int
    views_zeradas: int
    sem_url: int
    sem_jogo_detectado: int
    jogos_detectados: dict[str, int]


class VideoSemJogoOut(_Mirror):
    titulo: str
    canal: str
    plataforma: str
    views: int
    data_publicacao: str
    url: str
    texto_comentarios: str


class DescobertaOut(_Mirror):
    titulo: str
    canal: str
    url: str
    views: int
    perguntas: int
    candidato: str


# --- meu canal -----------------------------------------------------------------

class MeuVideoSemJogoOut(BaseModel):
    titulo: str
    data_publicacao: str
    views: int
    confianca_jogo: str
    fonte_deteccao: str
    url: str
    sugestao: str


class ComparacaoJogoOut(_Mirror):
    jogo: str
    score_final: float
    score_oportunidade: float
    score_evidencia_nicho: float
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    conclusao: str


class CandidatoRepeticaoOut(_Mirror):
    jogo: str
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    score_oportunidade: float
    tipo_video: str
    motivo: str


class JogoQueFalhouOut(_Mirror):
    jogo: str
    score_evidencia_nicho: float
    score_oportunidade: float
    score_resultado_real: float
    tipo_video: str
    melhor_video_url: str
    conclusao: str


# --- sistema / historico ---------------------------------------------------------

class StatusOut(_Mirror):
    chave_configurada: bool
    canal_configurado: bool
    videos_coletados: int
    meus_videos: int
    jogos: int
    canais: int
    videos_sem_jogo: int
    tem_relatorios: bool
    tem_historico: bool


class VariacaoJogoOut(_Mirror):
    nome: str
    posicao_anterior: int
    posicao_atual: int
    variacao_score_final: float
    variacao_oportunidade: float


class ComparacaoRankingsOut(_Mirror):
    data_anterior: str
    data_atual: str
    subiram: list[VariacaoJogoOut]
    cairam: list[VariacaoJogoOut]
    estaveis: list[VariacaoJogoOut]
    novos: list[str]
    sumiram: list[str]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_schemas.py -v`
Expected: passed

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas.py tests/test_api_schemas.py
git commit -m "feat(api): adiciona schemas de resposta"
```

---

### Task 5: `dependencies.py` — carregamento de dados por requisição

**Files:**
- Create: `src/api/dependencies.py`
- Test: `tests/test_api_dependencies.py`

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/test_api_dependencies.py`:

```python
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config
from api import dependencies


def test_carregar_jogos_le_do_data_dir(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    jogos = dependencies.carregar_jogos()

    assert len(jogos) == 1
    assert jogos[0].nome == "Repo"


def test_carregar_jogos_arquivo_ausente_devolve_lista_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    assert dependencies.carregar_jogos() == []


def test_carregar_jogos_arquivo_ilegivel_levanta_503(tmp_path, monkeypatch):
    caminho = tmp_path / "jogos_seed.csv"
    caminho.mkdir()  # forca um erro de leitura: e um diretorio, nao um arquivo
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    with pytest.raises(Exception) as excinfo:
        dependencies.carregar_jogos()
    assert getattr(excinfo.value, "status_code", None) == 503


def test_carregar_ranking_delega_para_ranking_service(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,1000,10,1,2026-05-01,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    ranking = dependencies.carregar_ranking()

    assert len(ranking) == 1
    assert ranking[0].jogo.nome == "Repo"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_dependencies.py -v`
Expected: `ModuleNotFoundError: No module named 'api.dependencies'`

- [ ] **Step 3: Criar `src/api/dependencies.py`**

```python
# Funcoes de carregamento por requisicao: leem os CSVs configurados em config.py e
# devolvem os dados ja no formato dos dataclasses internos, ou levantam 503 se o
# arquivo existir mas nao puder ser lido. Arquivo AUSENTE nao e erro: os leitores de
# CSV ja devolvem lista vazia nesse caso (mesmo comportamento da CLI).

import csv

from fastapi import HTTPException

import config
import ranking_service
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from meus_videos import ler_meus_videos
from watchlist import listar_jogos as _listar_jogos_watchlist


def _seguro(func, caminho, descricao: str):
    try:
        return func(caminho)
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel ler {descricao}: {erro}")


def carregar_jogos():
    return _seguro(ler_jogos_seed, config.DATA_DIR / "jogos_seed.csv", "jogos_seed.csv")


def carregar_canais():
    return _seguro(
        ler_canais_referencia, config.DATA_DIR / "canais_referencia.csv", "canais_referencia.csv"
    )


def carregar_videos():
    return _seguro(ler_videos_coletados, config.VIDEOS_CSV, "videos_coletados.csv")


def carregar_meus_videos():
    return _seguro(ler_meus_videos, config.MEUS_VIDEOS_CSV, "meus_videos.csv")


def carregar_watchlist():
    return _seguro(_listar_jogos_watchlist, config.WATCHLIST_CSV, "watchlist_jogos.csv")


def carregar_ranking(plataforma: str | None = None, top: int | None = None, desde=None):
    try:
        return ranking_service.carregar_ranking(
            config.DATA_DIR, config.VIDEOS_CSV, config.MEUS_VIDEOS_CSV, plataforma, top, desde
        )
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel montar o ranking: {erro}")
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_dependencies.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/api/dependencies.py tests/test_api_dependencies.py
git commit -m "feat(api): adiciona carregamento de dados por requisicao"
```

---

### Task 6: Router `/ranking` e `/oportunidades`

**Files:**
- Create: `src/api/routers/__init__.py` (vazio)
- Create: `src/api/routers/ranking.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_ranking.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_ranking.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def _preparar_dados(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,500000,20000,5000,2026-05-01,qual o nome do jogo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")


def test_ranking_devolve_lista_de_jogos(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/ranking")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["jogo"] == "Repo"
    assert corpo[0]["posicao"] == 1
    assert corpo[0]["videos"][0]["canal"] == "Canal"


def test_ranking_aplica_filtro_top(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/ranking", params={"top": 0})

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_ranking_data_invalida_devolve_422(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/ranking", params={"desde": "nao-e-uma-data"})

    assert resposta.status_code == 422


def test_ranking_sem_dados_devolve_lista_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    resposta = client.get("/ranking")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_oportunidades_devolve_lista(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    resposta = client.get("/oportunidades")

    assert resposta.status_code == 200
    assert resposta.json() == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_ranking.py -v`
Expected: 404 nas rotas (router ainda nao existe / nao esta incluido no app)

- [ ] **Step 3: Criar `src/api/routers/__init__.py`** (vazio)

- [ ] **Step 4: Criar `src/api/routers/ranking.py`**

```python
from datetime import date

from fastapi import APIRouter, Query

from api import dependencies
from api.schemas import OportunidadeOut, RankingItemOut, RankingVideoOut
from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia
from ranker import filtrar_oportunidades

router = APIRouter(tags=["ranking"])


def _video_out(video) -> RankingVideoOut:
    return RankingVideoOut(
        titulo=video.titulo,
        canal=video.canal,
        plataforma=video.plataforma,
        url=video.url,
        views=video.views,
        likes=video.likes,
        comentarios=video.comentarios,
        data_publicacao=video.data_publicacao,
        taxa_engajamento=round(calcular_taxa_engajamento(video) * 100, 1),
        views_por_dia=round(calcular_views_por_dia(video), 1),
    )


def _item_out(posicao: int, resultado) -> RankingItemOut:
    return RankingItemOut(
        posicao=posicao,
        jogo=resultado.jogo.nome,
        score_final=resultado.score_final,
        score_tendencia=resultado.score_tendencia,
        score_fit_canal=resultado.score_fit_canal,
        score_fit_real=resultado.score_fit_real,
        formato_sugerido=resultado.formato_sugerido,
        score_descoberta=resultado.score_descoberta,
        score_saturacao=resultado.score_saturacao,
        score_oportunidade=resultado.score_oportunidade,
        score_evidencia_criadores=resultado.score_evidencia_criadores,
        score_evidencia_nicho=resultado.score_evidencia_nicho,
        videos_encontrados=resultado.videos_encontrados,
        canais_diferentes=resultado.canais_diferentes,
        motivo=resultado.motivo,
        acao_recomendada=resultado.acao_recomendada,
        videos=[_video_out(video) for video in resultado.videos],
    )


@router.get("/ranking", response_model=list[RankingItemOut])
def obter_ranking(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    ranking = dependencies.carregar_ranking(plataforma, top, desde)
    return [_item_out(posicao, resultado) for posicao, resultado in enumerate(ranking, start=1)]


@router.get("/oportunidades", response_model=list[OportunidadeOut])
def obter_oportunidades(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    ranking = dependencies.carregar_ranking(plataforma, top, desde)
    oportunidades = filtrar_oportunidades(ranking)
    return [
        OportunidadeOut(
            posicao=posicao,
            jogo=resultado.jogo.nome,
            score_final=resultado.score_final,
            score_oportunidade=resultado.score_oportunidade,
            score_saturacao=resultado.score_saturacao,
            acao_recomendada=resultado.acao_recomendada,
            motivo=resultado.motivo,
        )
        for posicao, resultado in oportunidades
    ]
```

- [ ] **Step 5: Incluir o router em `src/api/main.py`**

Adicione ao fim de `src/api/main.py`:

```python
from api.routers import ranking

app.include_router(ranking.router)
```

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_ranking.py tests/test_api_app.py -v`
Expected: todos passed

- [ ] **Step 7: Rodar a suíte inteira**

Run: `py -3.14 -m pytest -q`
Expected: tudo passando (nenhuma regressão)

- [ ] **Step 8: Commit**

```bash
git add src/api/routers/__init__.py src/api/routers/ranking.py src/api/main.py tests/test_api_ranking.py
git commit -m "feat(api): adiciona rotas /ranking e /oportunidades"
```

---

### Task 7: Router `/evidencias/{jogo}`

**Files:**
- Create: `src/api/routers/evidencias.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_evidencias.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_evidencias.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def _preparar_dados(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios,tipo_video\n"
        "Repo e incrivel,Canal,youtube,https://y/1,500000,20000,5000,2026-05-01,,curto\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")


def test_evidencias_de_jogo_existente(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/evidencias/Repo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["jogo"] == "Repo"
    assert len(corpo["videos"]) == 1


def test_evidencias_filtra_por_tipo(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/evidencias/Repo", params={"tipo": "longo"})

    assert resposta.status_code == 404


def test_evidencias_jogo_inexistente_devolve_404(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/evidencias/JogoQueNaoExiste")

    assert resposta.status_code == 404
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_evidencias.py -v`
Expected: 404 genérico (rota não existe)

- [ ] **Step 3: Criar `src/api/routers/evidencias.py`**

```python
from fastapi import APIRouter, HTTPException, Query

from api import dependencies
from api.schemas import EvidenciaVideoOut, EvidenciasJogoOut
from evidencias_jogo import (
    calcular_score_evidencia_criadores,
    gerar_evidencias,
    resumir_evidencia_criadores,
)

router = APIRouter(tags=["evidencias"])


@router.get("/evidencias/{jogo}", response_model=EvidenciasJogoOut)
def obter_evidencias(jogo: str, tipo: str | None = Query(None)):
    ranking = dependencies.carregar_ranking()
    canais = dependencies.carregar_canais()
    evidencias_por_jogo = gerar_evidencias(ranking, canais)

    alvo = jogo.strip().casefold()
    encontrado = next(
        (nome for nome in evidencias_por_jogo if nome.casefold() == alvo), None
    )
    if encontrado is None or not evidencias_por_jogo[encontrado]:
        raise HTTPException(status_code=404, detail=f"Jogo nao encontrado: {jogo}")

    evidencias = evidencias_por_jogo[encontrado]
    if tipo:
        evidencias = [e for e in evidencias if e.tipo_video == tipo]
        if not evidencias:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum video do tipo '{tipo}' encontrado para o jogo: {encontrado}",
            )

    return EvidenciasJogoOut(
        jogo=encontrado,
        score_evidencia=calcular_score_evidencia_criadores(evidencias),
        resumo=resumir_evidencia_criadores(evidencias),
        videos=[EvidenciaVideoOut.model_validate(e) for e in evidencias],
    )
```

- [ ] **Step 4: Incluir o router em `src/api/main.py`**

```python
from api.routers import evidencias, ranking

app.include_router(ranking.router)
app.include_router(evidencias.router)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_evidencias.py -v`
Expected: 3 passed

- [ ] **Step 6: Rodar a suíte inteira e commitar**

Run: `py -3.14 -m pytest -q`

```bash
git add src/api/routers/evidencias.py src/api/main.py tests/test_api_evidencias.py
git commit -m "feat(api): adiciona rota /evidencias/{jogo}"
```

---

### Task 8: Router `/watchlist` e `/watchlist/ranking`

**Files:**
- Create: `src/api/routers/watchlist.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_watchlist.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_watchlist.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def test_watchlist_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WATCHLIST_CSV", tmp_path / "watchlist.csv")

    resposta = client.get("/watchlist")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_watchlist_lista_jogos_adicionados(tmp_path, monkeypatch):
    caminho = tmp_path / "watchlist.csv"
    caminho.write_text(
        "nome_jogo,data_adicao\nRepo,2026-05-01 10:00:00\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "WATCHLIST_CSV", caminho)

    resposta = client.get("/watchlist")

    assert resposta.json() == ["Repo"]


def test_watchlist_ranking_marca_jogo_fora_do_ranking(tmp_path, monkeypatch):
    caminho = tmp_path / "watchlist.csv"
    caminho.write_text(
        "nome_jogo,data_adicao\nJogoFantasma,2026-05-01 10:00:00\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "WATCHLIST_CSV", caminho)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    resposta = client.get("/watchlist/ranking")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo[0]["nome"] == "JogoFantasma"
    assert corpo[0]["posicao"] is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_watchlist.py -v`
Expected: 404 (rotas não existem)

- [ ] **Step 3: Criar `src/api/routers/watchlist.py`**

Reaproveita `cruzar_watchlist_com_ranking` de `main.py` (única função pura de cruzamento watchlist x ranking que já existe — evita duplicar a lógica).

```python
from datetime import date

from fastapi import APIRouter, Query

from api import dependencies
from api.schemas import WatchlistRankingItemOut
from main import cruzar_watchlist_com_ranking

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=list[str])
def obter_watchlist():
    return dependencies.carregar_watchlist()


@router.get("/watchlist/ranking", response_model=list[WatchlistRankingItemOut])
def obter_watchlist_ranking(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    nomes = dependencies.carregar_watchlist()
    ranking = dependencies.carregar_ranking(plataforma, top, desde)

    itens = []
    for nome, posicao, resultado in cruzar_watchlist_com_ranking(nomes, ranking):
        itens.append(
            WatchlistRankingItemOut(
                nome=nome,
                posicao=posicao,
                score_final=resultado.score_final if resultado else None,
                score_oportunidade=resultado.score_oportunidade if resultado else None,
                acao_recomendada=resultado.acao_recomendada if resultado else None,
                motivo=resultado.motivo if resultado else None,
            )
        )
    return itens
```

- [ ] **Step 4: Incluir o router em `src/api/main.py`**

```python
from api.routers import evidencias, ranking, watchlist

app.include_router(ranking.router)
app.include_router(evidencias.router)
app.include_router(watchlist.router)
```

**Atenção:** `main.py` faz `parser.parse_args(argv)` só dentro de `main()`, nunca no nível do módulo — então importar `cruzar_watchlist_com_ranking` de lá não dispara parsing de CLI nem `sys.exit`. Confirme isso lendo `src/main.py` linhas 85-90 se tiver dúvida antes de rodar.

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_watchlist.py -v`
Expected: 3 passed

- [ ] **Step 6: Rodar a suíte inteira e commitar**

Run: `py -3.14 -m pytest -q`

```bash
git add src/api/routers/watchlist.py src/api/main.py tests/test_api_watchlist.py
git commit -m "feat(api): adiciona rotas /watchlist e /watchlist/ranking"
```

---

### Task 9: Router `/meu-canal/*`

**Files:**
- Create: `src/api/routers/meu_canal.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_meu_canal.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_meu_canal.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def _preparar_meus_videos(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,500000,20000,5000,2026-05-01,\n",
        encoding="utf-8",
    )
    meus_videos_csv = tmp_path / "meus_videos.csv"
    meus_videos_csv.write_text(
        "video_id,data_coleta,data_publicacao,titulo,jogo_detectado,confianca_jogo,"
        "fonte_deteccao,url,views,likes,comentarios,tipo_video,score_resultado_real,status_analise\n"
        "vid1,2026-05-02,2026-05-01,Meu video sem jogo,,,,https://y/m1,100,1,0,curto,10,pendente\n"
        "vid2,2026-05-02,2026-05-01,Meu video do Repo,Repo,alta,descricao,https://y/m2,"
        "600000,30000,6000,curto,90,pendente\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", meus_videos_csv)


def test_meu_canal_sem_jogo(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    resposta = client.get("/meu-canal/sem-jogo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["titulo"] == "Meu video sem jogo"
    assert "sugestao" in corpo[0]


def test_meu_canal_comparacao(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    resposta = client.get("/meu-canal/comparacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo[0]["jogo"] == "Repo"
    assert corpo[0]["conclusao"] in {
        "ainda_nao_testado", "recomendacao_confirmada", "prometia_mas_nao_funcionou",
        "funcionou_melhor_que_o_esperado", "precisa_de_mais_testes",
    }


def test_meu_canal_repetir_e_falhos_respondem_200(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    assert client.get("/meu-canal/repetir").status_code == 200
    assert client.get("/meu-canal/falhos").status_code == 200
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_meu_canal.py -v`
Expected: 404 (rotas não existem)

- [ ] **Step 3: Criar `src/api/routers/meu_canal.py`**

```python
from fastapi import APIRouter

from api import dependencies
from api.schemas import CandidatoRepeticaoOut, ComparacaoJogoOut, JogoQueFalhouOut, MeuVideoSemJogoOut
from comparacao_meu_canal import comparar_recomendacoes_com_meu_canal
from jogos_falhos import jogos_que_nao_funcionaram
from meus_videos import listar_meus_videos_sem_jogo, sugestao_deteccao
from repetir_jogos import jogos_para_repetir

router = APIRouter(prefix="/meu-canal", tags=["meu-canal"])


@router.get("/sem-jogo", response_model=list[MeuVideoSemJogoOut])
def obter_meu_canal_sem_jogo():
    videos = listar_meus_videos_sem_jogo(config_meus_videos_csv())
    return [
        MeuVideoSemJogoOut(
            titulo=video.titulo,
            data_publicacao=video.data_publicacao,
            views=video.views,
            confianca_jogo=video.confianca_jogo,
            fonte_deteccao=video.fonte_deteccao,
            url=video.url,
            sugestao=sugestao_deteccao(video.titulo),
        )
        for video in videos
    ]


@router.get("/comparacao", response_model=list[ComparacaoJogoOut])
def obter_meu_canal_comparacao():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    comparacoes = comparar_recomendacoes_com_meu_canal(ranking, meus_videos)
    return [ComparacaoJogoOut.model_validate(c) for c in comparacoes]


@router.get("/repetir", response_model=list[CandidatoRepeticaoOut])
def obter_meu_canal_repetir():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    candidatos = jogos_para_repetir(ranking, meus_videos)
    return [CandidatoRepeticaoOut.model_validate(c) for c in candidatos]


@router.get("/falhos", response_model=list[JogoQueFalhouOut])
def obter_meu_canal_falhos():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    falhos = jogos_que_nao_funcionaram(ranking, meus_videos)
    return [JogoQueFalhouOut.model_validate(f) for f in falhos]


def config_meus_videos_csv():
    import config
    return config.MEUS_VIDEOS_CSV
```

> **Nota:** `config_meus_videos_csv()` existe só porque `listar_meus_videos_sem_jogo` (em `meus_videos.py`) recebe um caminho direto em vez de usar `dependencies.carregar_*`. Se preferir manter o padrão de erro 503 dos outros endpoints, troque essa chamada por `dependencies._seguro(listar_meus_videos_sem_jogo, config.MEUS_VIDEOS_CSV, "meus_videos.csv")` e importe `config` no topo do arquivo — funcionalmente equivalente, só reusa o wrapper de erro já testado no Task 5.

- [ ] **Step 4: Incluir o router em `src/api/main.py`**

```python
from api.routers import evidencias, meu_canal, ranking, watchlist

app.include_router(ranking.router)
app.include_router(evidencias.router)
app.include_router(watchlist.router)
app.include_router(meu_canal.router)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_meu_canal.py -v`
Expected: 3 passed

- [ ] **Step 6: Rodar a suíte inteira e commitar**

Run: `py -3.14 -m pytest -q`

```bash
git add src/api/routers/meu_canal.py src/api/main.py tests/test_api_meu_canal.py
git commit -m "feat(api): adiciona rotas /meu-canal/*"
```

---

### Task 10: Router `/diagnostico`, `/videos-sem-jogo`, `/descobertas-sem-jogo`

**Files:**
- Create: `src/api/routers/diagnostico.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_diagnostico.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_diagnostico.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def _preparar_dados(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,500000,20000,5000,2026-05-01,\n"
        "video misterioso,Canal,youtube,https://y/2,1000,10,1,2026-05-01,qual o nome do jogo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)


def test_diagnostico(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/diagnostico")

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 2


def test_videos_sem_jogo(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/videos-sem-jogo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["titulo"] == "video misterioso"


def test_descobertas_sem_jogo(tmp_path, monkeypatch):
    _preparar_dados(tmp_path, monkeypatch)

    resposta = client.get("/descobertas-sem-jogo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["titulo"] == "video misterioso"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_diagnostico.py -v`
Expected: 404 (rotas não existem)

- [ ] **Step 3: Criar `src/api/routers/diagnostico.py`**

```python
from fastapi import APIRouter

from api import dependencies
from api.schemas import DescobertaOut, DiagnosticoOut, VideoSemJogoOut
from descobertas import descobertas_sem_jogo
from diagnostico_dados import encontrar_videos_sem_jogo, gerar_diagnostico

router = APIRouter(tags=["diagnostico"])


@router.get("/diagnostico", response_model=DiagnosticoOut)
def obter_diagnostico():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return DiagnosticoOut.model_validate(gerar_diagnostico(videos, jogos))


@router.get("/videos-sem-jogo", response_model=list[VideoSemJogoOut])
def obter_videos_sem_jogo():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return [VideoSemJogoOut.model_validate(v) for v in encontrar_videos_sem_jogo(videos, jogos)]


@router.get("/descobertas-sem-jogo", response_model=list[DescobertaOut])
def obter_descobertas_sem_jogo():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return [DescobertaOut.model_validate(d) for d in descobertas_sem_jogo(videos, jogos)]
```

- [ ] **Step 4: Incluir o router em `src/api/main.py`**

```python
from api.routers import diagnostico, evidencias, meu_canal, ranking, watchlist

app.include_router(ranking.router)
app.include_router(evidencias.router)
app.include_router(watchlist.router)
app.include_router(meu_canal.router)
app.include_router(diagnostico.router)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_diagnostico.py -v`
Expected: 3 passed

- [ ] **Step 6: Rodar a suíte inteira e commitar**

Run: `py -3.14 -m pytest -q`

```bash
git add src/api/routers/diagnostico.py src/api/main.py tests/test_api_diagnostico.py
git commit -m "feat(api): adiciona rotas de diagnostico de dados"
```

---

### Task 11: Router `/status` e `/historico/comparacao`

**Files:**
- Create: `src/api/routers/sistema.py`
- Modify: `src/api/main.py`
- Test: `tests/test_api_sistema.py`

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_api_sistema.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def test_status(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")
    monkeypatch.setattr(config, "HISTORICO_CSV", tmp_path / "historico.csv")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")

    resposta = client.get("/status")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["videos_coletados"] == 0
    assert corpo["chave_configurada"] in {True, False}


def test_historico_comparacao_sem_dados_devolve_409(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "HISTORICO_CSV", tmp_path / "historico.csv")

    resposta = client.get("/historico/comparacao")

    assert resposta.status_code == 409


def test_historico_comparacao_com_duas_execucoes(tmp_path, monkeypatch):
    caminho = tmp_path / "historico.csv"
    caminho.write_text(
        "data_execucao,posicao,nome_jogo,score_final,score_tendencia,score_fit_canal,"
        "score_descoberta,score_saturacao,score_oportunidade,videos_encontrados,"
        "canais_diferentes,acao_recomendada,motivo\n"
        "2026-05-01 10:00:00,1,Repo,70,70,70,10,90,60,1,1,Testar,motivo\n"
        "2026-05-02 10:00:00,1,Repo,80,80,70,10,90,70,1,1,Testar,motivo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "HISTORICO_CSV", caminho)

    resposta = client.get("/historico/comparacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["data_atual"] == "2026-05-02 10:00:00"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `py -3.14 -m pytest tests/test_api_sistema.py -v`
Expected: 404 (rotas não existem)

- [ ] **Step 3: Criar `src/api/routers/sistema.py`**

```python
from fastapi import APIRouter, HTTPException

import config
from api.schemas import ComparacaoRankingsOut, StatusOut
from config import obter_meu_canal_youtube_id, obter_youtube_api_key
from historico_ranking import comparar_ultimas_execucoes
from status_sistema import coletar_status

router = APIRouter(tags=["sistema"])


@router.get("/status", response_model=StatusOut)
def obter_status():
    status = coletar_status(
        chave_configurada=obter_youtube_api_key() is not None,
        canal_configurado=obter_meu_canal_youtube_id() is not None,
        caminho_videos=config.VIDEOS_CSV,
        caminho_meus_videos=config.MEUS_VIDEOS_CSV,
        caminho_jogos=config.DATA_DIR / "jogos_seed.csv",
        caminho_canais=config.DATA_DIR / "canais_referencia.csv",
        caminho_historico=config.HISTORICO_CSV,
        dir_relatorios=config.REPORTS_DIR,
    )
    return StatusOut.model_validate(status)


@router.get("/historico/comparacao", response_model=ComparacaoRankingsOut)
def obter_historico_comparacao():
    comparacao = comparar_ultimas_execucoes(config.HISTORICO_CSV)
    if comparacao is None:
        raise HTTPException(
            status_code=409,
            detail="Historico insuficiente: sao necessarias pelo menos duas execucoes salvas.",
        )
    return ComparacaoRankingsOut.model_validate(comparacao)
```

**Atenção:** essa rota lê `config.VIDEOS_CSV`, `config.MEUS_VIDEOS_CSV`, `config.DATA_DIR`, `config.HISTORICO_CSV` e `config.REPORTS_DIR` na hora da chamada (via `config.<NOME>`, não `from config import <NOME>` direto nas variáveis) — assim o `monkeypatch.setattr(config, ...)` dos testes funciona. Não troque para `from config import VIDEOS_CSV` no topo do arquivo, isso capturaria o valor antigo e quebraria os testes com `monkeypatch`.

- [ ] **Step 4: Incluir o router em `src/api/main.py`**

```python
from api.routers import diagnostico, evidencias, meu_canal, ranking, sistema, watchlist

app.include_router(ranking.router)
app.include_router(evidencias.router)
app.include_router(watchlist.router)
app.include_router(meu_canal.router)
app.include_router(diagnostico.router)
app.include_router(sistema.router)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `py -3.14 -m pytest tests/test_api_sistema.py -v`
Expected: 3 passed

- [ ] **Step 6: Rodar a suíte inteira e commitar**

Run: `py -3.14 -m pytest -q`

```bash
git add src/api/routers/sistema.py src/api/main.py tests/test_api_sistema.py
git commit -m "feat(api): adiciona rotas /status e /historico/comparacao"
```

---

### Task 12: Documentar a API no README e checagem final

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Adicionar uma seção "API (opcional)" ao README**

Depois da seção "## Testing" em `README.md`, adicione:

```markdown
## API (optional)

A read-only FastAPI layer is available under `src/api/`, for a future web frontend and
external integrations. It reuses the same pure logic and CSV reads as the CLI — no
network calls, no database, no auth (local use only for now).

```bash
py -3.14 -m pip install -r requirements.txt
py -3.14 -m uvicorn api.main:app --reload --app-dir src
```

Then open `http://127.0.0.1:8000/docs` for the interactive OpenAPI docs. Endpoints mirror
the read-only CLI commands: `/ranking`, `/oportunidades`, `/evidencias/{jogo}`,
`/watchlist`, `/watchlist/ranking`, `/diagnostico`, `/videos-sem-jogo`,
`/descobertas-sem-jogo`, `/meu-canal/sem-jogo`, `/meu-canal/comparacao`,
`/meu-canal/repetir`, `/meu-canal/falhos`, `/historico/comparacao`, `/status`.
```

Ajuste também a linha do "Tech stack" que hoje diz "standard library only at runtime", citando que a API opcional é a única exceção (FastAPI/Uvicorn).

- [ ] **Step 2: Rodar a suíte inteira uma última vez**

Run: `py -3.14 -m pytest -q`
Expected: todos os testes passando (baseline 393 + os novos desta feature)

- [ ] **Step 3: Testar a API manualmente**

Run: `py -3.14 -m uvicorn api.main:app --app-dir src --port 8000`

Em outro terminal: `curl http://127.0.0.1:8000/status` — confirme uma resposta JSON válida. Pare o servidor (Ctrl+C) depois.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: documenta a API FastAPI opcional no README"
```

---

## Resumo dos endpoints entregues

| Rota | Router |
|---|---|
| `GET /ranking` | `routers/ranking.py` |
| `GET /oportunidades` | `routers/ranking.py` |
| `GET /evidencias/{jogo}` | `routers/evidencias.py` |
| `GET /watchlist` | `routers/watchlist.py` |
| `GET /watchlist/ranking` | `routers/watchlist.py` |
| `GET /meu-canal/sem-jogo` | `routers/meu_canal.py` |
| `GET /meu-canal/comparacao` | `routers/meu_canal.py` |
| `GET /meu-canal/repetir` | `routers/meu_canal.py` |
| `GET /meu-canal/falhos` | `routers/meu_canal.py` |
| `GET /diagnostico` | `routers/diagnostico.py` |
| `GET /videos-sem-jogo` | `routers/diagnostico.py` |
| `GET /descobertas-sem-jogo` | `routers/diagnostico.py` |
| `GET /status` | `routers/sistema.py` |
| `GET /historico/comparacao` | `routers/sistema.py` |

Fora de escopo (fases futuras, conforme o spec): endpoints de escrita, autenticação, cache/banco de dados.
