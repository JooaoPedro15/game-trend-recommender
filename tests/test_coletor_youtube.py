import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coletor_youtube
from coletor_youtube import _item_para_video, coletar_video_por_id


# Simula o objeto devolvido por urlopen: context manager com read() devolvendo JSON.
class _RespostaFake:
    def __init__(self, payload):
        self._texto = json.dumps(payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._texto


# Monta um item fake no formato da YouTube Data API.
def _item(views="12345", likes="678", comentarios="90", com_stats=True):
    item = {
        "snippet": {
            "title": "Esse jogo me quebrou",
            "channelTitle": "Canal Teste",
            "publishedAt": "2026-05-01T12:00:00Z",
        },
    }
    if com_stats:
        item["statistics"] = {
            "viewCount": views,
            "likeCount": likes,
            "commentCount": comentarios,
        }
    return item


# --- Conversao (mapper puro, sem rede) ---

def test_item_para_video_converte_campos():
    video = _item_para_video(_item(), "VID123")

    assert video.titulo == "Esse jogo me quebrou"
    assert video.canal == "Canal Teste"
    assert video.plataforma == "youtube"
    assert video.url == "https://www.youtube.com/watch?v=VID123"
    assert video.views == 12345
    assert video.likes == 678
    assert video.comentarios == 90
    assert video.data_publicacao == "2026-05-01"


def test_item_para_video_sem_estatisticas_usa_zero():
    video = _item_para_video(_item(com_stats=False), "VID123")

    assert video.views == 0
    assert video.likes == 0
    assert video.comentarios == 0


# --- Chamada completa com urlopen mockado (sem rede, chave fake) ---

def test_coletar_video_por_id_com_resposta_fake(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        lambda url, timeout=10: _RespostaFake({"items": [_item()]}),
    )

    video = coletar_video_por_id("VID123")

    assert video is not None
    assert video.titulo == "Esse jogo me quebrou"
    assert video.plataforma == "youtube"
    assert video.views == 12345


def test_coletar_video_por_id_nao_encontrado_retorna_none(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        lambda url, timeout=10: _RespostaFake({"items": []}),
    )

    assert coletar_video_por_id("VID_INEXISTENTE") is None


# --- Chave ausente: erro claro, sem tocar a rede ---

def test_coletar_video_por_id_sem_chave_levanta_erro(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        coletar_video_por_id("VID123")
