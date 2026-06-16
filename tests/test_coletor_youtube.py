import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coletor_youtube
from coletor_youtube import (
    _item_para_video,
    coletar_canal,
    coletar_comentarios,
    coletar_detalhe_video,
    coletar_detalhes_do_canal,
    coletar_video_por_id,
    coletar_videos_por_ids,
    listar_ids_recentes_do_canal,
    listar_videos_recentes_do_canal,
    ler_ids_de_arquivo,
    obter_playlist_uploads,
)
from leitor_csv import ler_videos_coletados
from modelos import VideoColetado


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


# --- Coleta em lote por arquivo de ids (sem rede) ---

def test_ler_ids_ignora_vazios_e_repetidos(tmp_path):
    arquivo = tmp_path / "ids.txt"
    arquivo.write_text("VID1\n\nVID2\n   \nVID1\n", encoding="utf-8")

    assert ler_ids_de_arquivo(arquivo) == ["VID1", "VID2"]


def test_coletar_videos_por_ids_conta_e_salva(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _fake_por_id(video_id, caminho_cache=None):
        urls = {"VID1": "https://y/1", "VID2": "https://y/2", "VID1DUP": "https://y/1"}
        if video_id not in urls:
            return None
        return VideoColetado(
            titulo="jogo " + video_id,
            canal="Canal Teste",
            plataforma="youtube",
            url=urls[video_id],
            views=1,
            likes=0,
            comentarios=0,
            data_publicacao="2026-05-01",
            texto_comentarios="",
        )

    monkeypatch.setattr(coletor_youtube, "coletar_video_por_id", _fake_por_id)

    arquivo = tmp_path / "ids.txt"
    arquivo.write_text("VID1\nVID2\nVIDX\nVID1DUP\n", encoding="utf-8")
    destino = tmp_path / "videos.csv"

    resumo = coletar_videos_por_ids(arquivo, destino)

    assert resumo == {"lidos": 4, "encontrados": 3, "salvos": 2, "duplicados": 1, "erros": 1}
    salvos = ler_videos_coletados(destino)
    assert [video.titulo for video in salvos] == ["jogo VID1", "jogo VID2"]
    assert all(video.plataforma == "youtube" for video in salvos)


def test_coletar_videos_por_ids_sem_chave_levanta_erro(monkeypatch, tmp_path):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    arquivo = tmp_path / "ids.txt"
    arquivo.write_text("VID1\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        coletar_videos_por_ids(arquivo, tmp_path / "videos.csv")


# --- Coleta por canal (fake client roteando os 3 endpoints) ---

# Fake do _get_json: channels -> uploads playlist, playlistItems -> ids, videos -> dados.
def _fake_get_json(url):
    if "/channels" in url:
        return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
    if "/playlistItems" in url:
        n = int(parse_qs(urlparse(url).query)["maxResults"][0])
        return {"items": [{"contentDetails": {"videoId": f"VID{i}"}} for i in range(n)]}
    if "/videos" in url:
        vid = parse_qs(urlparse(url).query)["id"][0]
        return {
            "items": [
                {
                    "snippet": {
                        "title": f"jogo {vid}",
                        "channelTitle": "Canal",
                        "publishedAt": "2026-05-01T00:00:00Z",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                }
            ]
        }
    return {"items": []}


def test_obter_playlist_uploads(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)

    assert obter_playlist_uploads("UC_X") == "UU_X"


def test_listar_ids_respeita_limite(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)

    assert listar_ids_recentes_do_canal("UC_X", 3) == ["VID0", "VID1", "VID2"]


def test_listar_ids_canal_inexistente_retorna_vazio(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", lambda url: {"items": []})

    assert listar_ids_recentes_do_canal("UC_X", 5) == []


def test_listar_ids_canal_sem_videos_retorna_vazio(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _so_uploads(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        return {"items": []}

    monkeypatch.setattr(coletor_youtube, "_get_json", _so_uploads)

    assert listar_ids_recentes_do_canal("UC_X", 5) == []


# Fake que inclui snippet.title nos playlistItems, para testar a versao com titulos.
def _fake_get_json_com_titulo(url):
    if "/channels" in url:
        return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
    if "/playlistItems" in url:
        n = int(parse_qs(urlparse(url).query)["maxResults"][0])
        return {
            "items": [
                {
                    "contentDetails": {"videoId": f"VID{i}"},
                    "snippet": {"title": f"meu video {i}"},
                }
                for i in range(n)
            ]
        }
    return {"items": []}


def test_listar_videos_recentes_traz_id_e_titulo(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_com_titulo)

    videos = listar_videos_recentes_do_canal("UC_X", 2)

    assert videos == [
        {"video_id": "VID0", "titulo": "meu video 0"},
        {"video_id": "VID1", "titulo": "meu video 1"},
    ]


def test_listar_videos_recentes_canal_inexistente_retorna_vazio(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", lambda url: {"items": []})

    assert listar_videos_recentes_do_canal("UC_X", 10) == []


def test_coletar_canal_converte_e_salva(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)

    destino = tmp_path / "videos.csv"
    cache = tmp_path / "cache.json"

    resumo = coletar_canal("UC_X", destino, limite=2, caminho_cache=cache)

    assert resumo == {"lidos": 2, "encontrados": 2, "salvos": 2, "duplicados": 0, "erros": 0}
    salvos = ler_videos_coletados(destino)
    assert [video.titulo for video in salvos] == ["jogo VID0", "jogo VID1"]
    assert all(video.plataforma == "youtube" for video in salvos)


# Fake de videos.list com snippet/statistics/contentDetails; duracao varia pelo id.
def _fake_get_json_detalhe(url):
    if "/videos" in url:
        vid = parse_qs(urlparse(url).query)["id"][0]
        duracoes = {"CURTO": "PT45S", "LONGO": "PT5M30S", "ZERO": "P0D"}
        return {
            "items": [
                {
                    "snippet": {
                        "title": f"titulo {vid}",
                        "channelTitle": "Meu Canal",
                        "description": f"descricao {vid}",
                        "tags": ["jogo", "gameplay"],
                        "publishedAt": "2026-05-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": duracoes.get(vid, "PT2M")},
                }
            ]
        }
    return {"items": []}


def test_coletar_detalhe_video_traz_descricao_tags_e_duracao(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_detalhe)

    detalhe = coletar_detalhe_video("CURTO")

    assert detalhe.video_id == "CURTO"
    assert detalhe.descricao == "descricao CURTO"
    assert detalhe.tags == ["jogo", "gameplay"]
    assert detalhe.duracao_segundos == 45
    assert detalhe.tipo_video == "curto"
    assert detalhe.url == "https://www.youtube.com/watch?v=CURTO"
    assert (detalhe.views, detalhe.likes, detalhe.comentarios) == (1000, 100, 10)


def test_tipo_video_longo_acima_de_60s(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_detalhe)

    detalhe = coletar_detalhe_video("LONGO")

    assert detalhe.duracao_segundos == 330
    assert detalhe.tipo_video == "longo"


def test_tipo_video_desconhecido_sem_duracao(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_detalhe)

    detalhe = coletar_detalhe_video("ZERO")

    assert detalhe.duracao_segundos == 0
    assert detalhe.tipo_video == "desconhecido"


def test_tipo_video_live_por_sinal(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _fake_live(url):
        return {
            "items": [
                {
                    "snippet": {
                        "title": "live",
                        "channelTitle": "Meu Canal",
                        "publishedAt": "2026-05-01T00:00:00Z",
                        "liveBroadcastContent": "live",
                    },
                    "statistics": {},
                    "contentDetails": {"duration": "PT0S"},
                }
            ]
        }

    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_live)

    assert coletar_detalhe_video("L").tipo_video == "live"


def test_coletar_detalhe_video_nao_encontrado_retorna_none(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", lambda url: {"items": []})

    assert coletar_detalhe_video("XYZ") is None


# Fake completo: channels -> uploads, playlistItems -> ids, videos -> detalhe curto.
def _fake_get_json_canal_detalhe(url):
    if "/channels" in url:
        return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
    if "/playlistItems" in url:
        n = int(parse_qs(urlparse(url).query)["maxResults"][0])
        return {"items": [{"contentDetails": {"videoId": f"VID{i}"}} for i in range(n)]}
    if "/videos" in url:
        vid = parse_qs(urlparse(url).query)["id"][0]
        return {
            "items": [
                {
                    "snippet": {
                        "title": f"titulo {vid}",
                        "channelTitle": "Meu Canal",
                        "description": "desc",
                        "tags": ["g"],
                        "publishedAt": "2026-05-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "5", "likeCount": "1", "commentCount": "0"},
                    "contentDetails": {"duration": "PT30S"},
                }
            ]
        }
    return {"items": []}


def test_coletar_detalhes_do_canal(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_canal_detalhe)

    detalhes = coletar_detalhes_do_canal("UC_X", 2)

    assert [d.video_id for d in detalhes] == ["VID0", "VID1"]
    assert all(d.tipo_video == "curto" for d in detalhes)
    assert detalhes[0].tags == ["g"]


# Resposta fake de commentThreads (context manager com read() devolvendo JSON).
class _RespostaComentariosFake:
    def __init__(self, textos):
        self._textos = textos

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {
                "items": [
                    {"snippet": {"topLevelComment": {"snippet": {"textDisplay": t}}}}
                    for t in self._textos
                ]
            }
        )


def _erro_403(reason):
    corpo = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode("utf-8")
    return HTTPError("url", 403, "Forbidden", {}, io.BytesIO(corpo))


def test_coletar_comentarios_devolve_so_o_texto(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    textos = ["qual o nome do jogo?", "e o Schedule I", "muito bom"]
    monkeypatch.setattr(
        coletor_youtube, "urlopen", lambda url, timeout=10: _RespostaComentariosFake(textos)
    )

    assert coletar_comentarios("ABC", 50) == textos


def test_coletar_comentarios_respeita_limite(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    textos = [f"comentario {i}" for i in range(10)]
    monkeypatch.setattr(
        coletor_youtube, "urlopen", lambda url, timeout=10: _RespostaComentariosFake(textos)
    )

    assert coletar_comentarios("ABC", 3) == ["comentario 0", "comentario 1", "comentario 2"]


def test_coletar_comentarios_desativados_retorna_vazio(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _raise(url, timeout=10):
        raise _erro_403("commentsDisabled")

    monkeypatch.setattr(coletor_youtube, "urlopen", _raise)

    assert coletar_comentarios("ABC", 50) == []


def test_coletar_comentarios_outro_403_levanta_erro(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _raise(url, timeout=10):
        raise _erro_403("quotaExceeded")

    monkeypatch.setattr(coletor_youtube, "urlopen", _raise)

    with pytest.raises(RuntimeError):
        coletar_comentarios("ABC", 50)
