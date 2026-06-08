import json
from dataclasses import asdict
from pathlib import Path

from modelos import VideoColetado


BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_PATH = BASE_DIR / "data" / "cache" / "youtube_videos.json"


# Le o cache (video_id -> dados do video). Retorna {} se nao existir ou estiver vazio.
def carregar_cache(caminho: str | Path = CACHE_PATH) -> dict:
    caminho = Path(caminho)
    if not caminho.exists() or caminho.stat().st_size == 0:
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


# Devolve o VideoColetado guardado para o video_id, ou None se nao estiver no cache.
def buscar_no_cache(video_id: str, caminho: str | Path = CACHE_PATH) -> VideoColetado | None:
    dados = carregar_cache(caminho).get(video_id)
    if dados is None:
        return None
    return VideoColetado(**dados)


# Salva um VideoColetado no cache sob o video_id (cria a pasta data/cache se preciso).
def salvar_no_cache(video_id: str, video: VideoColetado, caminho: str | Path = CACHE_PATH) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cache = carregar_cache(caminho)
    cache[video_id] = asdict(video)
    caminho.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
