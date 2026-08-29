import io
import json
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
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
    coletar_detalhes_em_lote,
    coletar_textos_comentarios,
    coletar_video_por_id,
    coletar_videos_por_ids,
    listar_ids_recentes_do_canal,
    listar_todos_ids_do_canal,
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
        ids = parse_qs(urlparse(url).query)["id"][0].split(",")
        return {
            "items": [
                {
                    "id": vid,
                    "snippet": {
                        "title": f"jogo {vid}",
                        "channelTitle": "Canal",
                        "description": "",
                        "tags": [],
                        "publishedAt": "2026-05-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                    "contentDetails": {"duration": "PT45S"},
                }
                for vid in ids
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


def test_coletar_comentarios_inclui_respostas_e_respostas_adicionais(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _urlopen(url, timeout=10):
        if "commentThreads" in url:
            return _RespostaFake(
                {
                    "items": [
                        {
                            "snippet": {
                                "totalReplyCount": 2,
                                "topLevelComment": {
                                    "id": "C1",
                                    "snippet": {"textDisplay": "comentario principal"},
                                },
                            },
                            "replies": {
                                "comments": [
                                    {"snippet": {"textDisplay": "resposta carregada"}}
                                ]
                            },
                        }
                    ]
                }
            )
        if "comments" in url:
            return _RespostaFake(
                {
                    "items": [
                        {"snippet": {"textDisplay": "resposta adicional"}},
                    ]
                }
            )
        raise AssertionError(f"endpoint inesperado: {url}")

    monkeypatch.setattr(coletor_youtube, "urlopen", _urlopen)

    assert coletar_comentarios("ABC", 10) == [
        "comentario principal",
        "resposta carregada",
        "resposta adicional",
    ]


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


# --- Coleta completa: paginacao de ids e detalhes em lote (Sprint 10.9) ---

# channels -> uploads; playlistItems pagina em 2 (VID0,VID1 | VID2); videos.list em lote.
def _fake_get_json_paginado(url):
    if "/channels" in url:
        return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
    if "/playlistItems" in url:
        token = parse_qs(urlparse(url).query).get("pageToken", [None])[0]
        if token is None:
            return {
                "items": [
                    {"contentDetails": {"videoId": "VID0"}},
                    {"contentDetails": {"videoId": "VID1"}},
                ],
                "nextPageToken": "P2",
            }
        return {"items": [{"contentDetails": {"videoId": "VID2"}}]}
    if "/videos" in url:
        ids = parse_qs(urlparse(url).query)["id"][0].split(",")
        return {
            "items": [
                {
                    "id": vid,
                    "snippet": {
                        "title": f"titulo {vid}",
                        "channelTitle": "Meu Canal",
                        "description": "",
                        "tags": [],
                        "publishedAt": "2026-05-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "1", "likeCount": "0", "commentCount": "0"},
                    "contentDetails": {"duration": "PT1M"},
                }
                for vid in ids
            ]
        }
    return {"items": []}


def test_listar_todos_ids_pagina_ate_o_fim(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_paginado)

    assert listar_todos_ids_do_canal("UC_X") == ["VID0", "VID1", "VID2"]


def test_listar_todos_ids_pagina_tres_paginas_e_nao_para_em_50(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _fake_tres_paginas(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        if "/playlistItems" in url:
            token = parse_qs(urlparse(url).query).get("pageToken", [None])[0]
            if token is None:
                inicio, proximo = 0, "P2"
            elif token == "P2":
                inicio, proximo = 50, "P3"
            else:
                inicio, proximo = 100, None
            payload = {
                "items": [
                    {"contentDetails": {"videoId": f"VID{i}"}}
                    for i in range(inicio, inicio + 25)
                ]
            }
            if proximo:
                payload["nextPageToken"] = proximo
            return payload
        return {"items": []}

    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_tres_paginas)

    ids = listar_todos_ids_do_canal("UC_X")

    assert len(ids) == 75
    assert ids[0] == "VID0"
    assert ids[-1] == "VID124"


def test_listar_todos_ids_respeita_teto(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_paginado)

    assert listar_todos_ids_do_canal("UC_X", limite_maximo=2) == ["VID0", "VID1"]


def test_coletar_detalhes_em_lote_usa_id_do_item(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_paginado)

    detalhes = coletar_detalhes_em_lote(["VID0", "VID2"])

    assert {d.video_id for d in detalhes} == {"VID0", "VID2"}
    assert detalhes[0].url == "https://www.youtube.com/watch?v=VID0"


def test_coletar_detalhes_em_lote_vazio_nao_chama_api(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    assert coletar_detalhes_em_lote([]) == []


# --- Falha de rede (nao-HTTP) vira RuntimeError, nunca URLError cru ---
#
# URLError e irmao do HTTPError na hierarquia do urllib e NAO e RuntimeError. Antes ele
# escapava ate o terminal como stack trace, porque os comandos do main.py so capturam
# RuntimeError. Estes testes travam os dois lados do contrato: falha permanente vira
# RuntimeError na hora, e timeout continua sendo retentado antes de desistir.

def _urlopen_que_falha(erro):
    def _falhar(url, timeout=10):
        raise erro

    return _falhar


def test_conexao_recusada_vira_runtime_error(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        _urlopen_que_falha(URLError(ConnectionRefusedError("conexao recusada"))),
    )

    with pytest.raises(RuntimeError, match="Falha de rede"):
        coletar_video_por_id("VID123")


def test_timeout_no_video_e_retentado_e_vira_runtime_error(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    tentativas = []

    def _timeout(url, timeout=10):
        tentativas.append(url)
        raise URLError(socket.timeout("timed out"))

    monkeypatch.setattr(coletor_youtube, "urlopen", _timeout)

    with pytest.raises(RuntimeError, match="Timeout"):
        coletar_video_por_id("VID123")

    assert len(tentativas) == 3


def test_falha_de_rede_no_lote_e_contada_como_erro(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        _urlopen_que_falha(URLError(ConnectionRefusedError("conexao recusada"))),
    )
    arquivo = tmp_path / "ids.txt"
    arquivo.write_text("VID1\nVID2\n", encoding="utf-8")

    resumo = coletar_videos_por_ids(arquivo, tmp_path / "videos.csv", None)

    assert resumo["lidos"] == 2
    assert resumo["erros"] == 2
    assert resumo["salvos"] == 0


def test_falha_de_rede_ao_listar_canal_vira_runtime_error(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        _urlopen_que_falha(URLError(ConnectionRefusedError("conexao recusada"))),
    )

    with pytest.raises(RuntimeError, match="Falha de rede"):
        obter_playlist_uploads("UC_X")


def test_falha_de_rede_nos_comentarios_vira_runtime_error(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        _urlopen_que_falha(URLError(ConnectionRefusedError("conexao recusada"))),
    )

    with pytest.raises(RuntimeError, match="Falha de rede"):
        coletar_comentarios("VID123")


# ---------------------------------------------------------------------------
# Classificacao dos comentarios na coleta (dono / pergunta / autor anonimo).
# ---------------------------------------------------------------------------


# prefixo mantem os ids de resposta unicos entre threads: ids repetidos sao descartados
# pela deduplicacao da coleta, e o teste mediria o dedupe em vez do que quer medir.
def _thread_com_autores(topo, autor_topo, respostas, prefixo="T1"):
    return {
        "snippet": {
            "totalReplyCount": len(respostas),
            "topLevelComment": {
                "id": f"C{prefixo}",
                "snippet": {"textDisplay": topo, "authorChannelId": {"value": autor_topo}},
            },
        },
        "replies": {
            "comments": [
                {
                    "id": f"R{prefixo}_{indice}",
                    "snippet": {"textDisplay": texto, "authorChannelId": {"value": autor}},
                }
                for indice, (texto, autor) in enumerate(respostas)
            ]
        },
    }


def _patch_threads(monkeypatch, threads):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(
        coletor_youtube, "urlopen", lambda url, timeout=10: _RespostaFake({"items": threads})
    )


def test_coleta_marca_o_comentario_do_dono(monkeypatch):
    _patch_threads(
        monkeypatch,
        [_thread_com_autores("Nome do jogo?", "UC_A", [("lava and aqua", "UC_DONO")])],
    )

    coleta = coletar_textos_comentarios("VID", 50, channel_id_dono="UC_DONO")

    assert [c.do_dono for c in coleta.analisados] == [False, True]


def test_coleta_marca_resposta_dentro_de_thread_que_pergunta_o_jogo(monkeypatch):
    _patch_threads(
        monkeypatch,
        [
            _thread_com_autores("Nome do jogo?", "UC_A", [("lava and aqua", "UC_DONO")], "T1"),
            _thread_com_autores("Video muito bom", "UC_B", [("valeu", "UC_DONO")], "T2"),
        ],
    )

    coleta = coletar_textos_comentarios("VID", 50, channel_id_dono="UC_DONO")

    # O comentario do topo nunca responde a si mesmo; so as respostas herdam a pergunta.
    assert [c.responde_pergunta_de_jogo for c in coleta.analisados] == [False, True, False, False]


def test_coleta_da_indices_diferentes_a_autores_diferentes(monkeypatch):
    _patch_threads(
        monkeypatch,
        [
            _thread_com_autores(
                "Nome do jogo?",
                "UC_A",
                [("lava and aqua", "UC_B"), ("lava and aqua", "UC_C"), ("isso ai", "UC_B")],
            )
        ],
    )

    coleta = coletar_textos_comentarios("VID", 50, channel_id_dono="UC_DONO")
    indices = [c.autor_indice for c in coleta.analisados]

    # UC_A, UC_B, UC_C, UC_B -> o mesmo autor recebe sempre o mesmo indice.
    assert indices == [0, 1, 2, 1]


# Sem o id do dono nao ha como marcar ninguem como dono, e a coleta segue funcionando.
def test_coleta_sem_id_do_dono_nao_marca_ninguem(monkeypatch):
    _patch_threads(
        monkeypatch,
        [_thread_com_autores("Nome do jogo?", "UC_A", [("lava and aqua", "UC_DONO")])],
    )

    coleta = coletar_textos_comentarios("VID", 50)

    assert [c.do_dono for c in coleta.analisados] == [False, False]


# O objeto devolvido pela coleta nao pode carregar o id do autor para fora.
def test_comentario_analisado_nao_carrega_id_de_autor(monkeypatch):
    _patch_threads(
        monkeypatch,
        [_thread_com_autores("Nome do jogo?", "UC_A", [("lava and aqua", "UC_DONO")])],
    )

    coleta = coletar_textos_comentarios("VID", 50, channel_id_dono="UC_DONO")

    campos = vars(coleta.analisados[0])
    assert "UC_A" not in str(campos.values())
    assert set(campos) == {"texto", "do_dono", "responde_pergunta_de_jogo", "autor_indice"}


# --- O detalhe precisa saber de que canal veio ---
#
# O ranker casa peso e peso_similaridade pelo NOME do canal. Um detalhe sem canal nao pode
# virar VideoColetado sem perder a calibracao inteira, em silencio.

def test_detalhe_guarda_o_nome_do_canal(monkeypatch):
    import coletor_youtube

    def _fake(url):
        return {
            "items": [
                {
                    "id": "VID1",
                    "snippet": {
                        "title": "MEU BARCO NAUFRAGO",
                        "channelTitle": "Lozao",
                        "description": "nesse video eu trouxe How to fish",
                        "tags": ["pescaria"],
                        "publishedAt": "2026-08-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "90362", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": "PT8M"},
                }
            ]
        }

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake)

    detalhe = coletor_youtube.coletar_detalhe_video("VID1")

    assert detalhe.canal == "Lozao"


def test_detalhe_em_lote_tambem_guarda_o_canal(monkeypatch):
    import coletor_youtube

    def _fake(url):
        return {
            "items": [
                {
                    "id": vid,
                    "snippet": {
                        "title": f"video {vid}",
                        "channelTitle": "ElCamacho24",
                        "description": "",
                        "tags": [],
                        "publishedAt": "2026-08-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                    "contentDetails": {"duration": "PT30S"},
                }
                for vid in ["VID1", "VID2"]
            ]
        }

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake)

    detalhes = coletor_youtube.coletar_detalhes_em_lote(["VID1", "VID2"])

    assert [d.canal for d in detalhes] == ["ElCamacho24", "ElCamacho24"]


# --- Coleta de canal em lote ---
#
# Antes: uma chamada videos.list por video (1 unidade cada) e sem contentDetails, entao
# tipo_video ficava "desconhecido" e descricao/tags eram descartadas. Agora: um lote de ate
# 50 por chamada, com os tres campos.

def _fake_canal_em_lote(chamadas):
    def _fake(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        if "/playlistItems" in url:
            return {
                "items": [
                    {"contentDetails": {"videoId": "VID0"}},
                    {"contentDetails": {"videoId": "VID1"}},
                ]
            }
        if "/videos" in url:
            chamadas.append(url)
            ids = parse_qs(urlparse(url).query)["id"][0].split(",")
            return {
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "title": f"video {vid}",
                            "channelTitle": "Lozao",
                            "description": f"nesse video eu trouxe o jogo {vid}",
                            "tags": ["gameplay"],
                            "publishedAt": "2026-08-01T00:00:00Z",
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "10",
                            "commentCount": "5",
                        },
                        "contentDetails": {"duration": "PT45S"},
                    }
                    for vid in ids
                ]
            }
        return {"items": []}

    return _fake


def test_coletar_canal_usa_uma_unica_chamada_de_videos(monkeypatch, tmp_path):
    chamadas = []
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote(chamadas))
    destino = tmp_path / "videos_coletados.csv"

    resumo = coletor_youtube.coletar_canal("UC_X", destino, limite=2, caminho_cache=None)

    assert len(chamadas) == 1  # dois videos, uma chamada
    assert resumo["salvos"] == 2


def test_coletar_canal_guarda_descricao_tags_e_tipo(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))
    destino = tmp_path / "videos_coletados.csv"

    coletor_youtube.coletar_canal("UC_X", destino, limite=2, caminho_cache=None)

    videos = {v.url: v for v in ler_videos_coletados(destino)}
    primeiro = videos["https://www.youtube.com/watch?v=VID0"]
    assert primeiro.canal == "Lozao"
    assert primeiro.descricao == "nesse video eu trouxe o jogo VID0"
    assert primeiro.tags == ["gameplay"]
    assert primeiro.tipo_video == "curto"  # PT45S
