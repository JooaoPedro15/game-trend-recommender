import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coletor_youtube
from cache_youtube import buscar_no_cache, carregar_cache, salvar_no_cache
from coletor_youtube import coletar_video_por_id
from modelos import VideoColetado


# Resposta fake da YouTube API (context manager com read() devolvendo JSON).
class _RespostaFake:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {
                "items": [
                    {
                        "snippet": {
                            "title": "Jogo X",
                            "channelTitle": "Canal",
                            "publishedAt": "2026-05-01T00:00:00Z",
                        },
                        "statistics": {"viewCount": "100", "likeCount": "10", "commentCount": "2"},
                    }
                ]
            }
        )


# Cria um VideoColetado de teste.
def _video(url="https://www.youtube.com/watch?v=ABC"):
    return VideoColetado(
        titulo="Jogo X",
        canal="Canal",
        plataforma="youtube",
        url=url,
        views=100,
        likes=10,
        comentarios=2,
        data_publicacao="2026-05-01",
        texto_comentarios="",
    )


# --- cache: salvar / buscar / carregar ---

def test_salva_e_le_video(tmp_path):
    caminho = tmp_path / "cache.json"
    video = _video()

    salvar_no_cache("ABC", video, caminho)

    assert buscar_no_cache("ABC", caminho) == video


def test_buscar_id_inexistente_retorna_none(tmp_path):
    caminho = tmp_path / "cache.json"
    salvar_no_cache("ABC", _video(), caminho)

    assert buscar_no_cache("OUTRO", caminho) is None


def test_carregar_cache_inexistente_retorna_vazio(tmp_path):
    assert carregar_cache(tmp_path / "nao_existe.json") == {}


# --- coletor + cache: API so e chamada no miss ---

def test_api_so_e_chamada_quando_nao_esta_no_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    caminho = tmp_path / "cache.json"
    chamadas = {"n": 0}

    def _fake_urlopen(url, timeout=10):
        chamadas["n"] += 1
        return _RespostaFake()

    monkeypatch.setattr(coletor_youtube, "urlopen", _fake_urlopen)

    primeiro = coletar_video_por_id("ABC", caminho)  # miss -> chama API + salva
    segundo = coletar_video_por_id("ABC", caminho)   # hit -> nao chama API

    assert chamadas["n"] == 1
    assert primeiro == segundo
    assert primeiro.titulo == "Jogo X"
