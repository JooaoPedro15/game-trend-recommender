import io
import json
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coletor_youtube
import main as main_mod
from analise_meu_canal import analisar_canal_completo, analisar_meu_canal
from leitor_csv import _ler_linhas
from main import coletar_meu_canal_interativo
from meus_videos import salvar_meu_video
from modelos import JogoSeed, MeuVideo


def _jogos() -> list[JogoSeed]:
    return [
        JogoSeed(nome="Resident Evil", aliases=["re4", "resident"], genero="terror", fit_inicial=0.6)
    ]


# Fake do _get_json roteando os 3 endpoints. VID0 cita o jogo no titulo; os demais nao.
def _fake_get_json(url):
    if "/channels" in url:
        return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
    if "/playlistItems" in url:
        n = int(parse_qs(urlparse(url).query)["maxResults"][0])
        return {"items": [{"contentDetails": {"videoId": f"VID{i}"}} for i in range(n)]}
    if "/videos" in url:
        vid = parse_qs(urlparse(url).query)["id"][0]
        titulo = "Joguei Resident Evil ate tarde" if vid == "VID0" else f"video sem jogo {vid}"
        return {
            "items": [
                {
                    "snippet": {
                        "title": titulo,
                        "channelTitle": "Meu Canal",
                        "description": "",
                        "tags": [],
                        "publishedAt": "2026-06-10T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": "PT5M"},
                }
            ]
        }
    return {"items": []}


# urlopen fake para commentThreads: sempre sem comentarios.
class _SemComentarios:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"items": []})


def _patch_api(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)
    monkeypatch.setattr(coletor_youtube, "urlopen", lambda url, timeout=10: _SemComentarios())


def test_analisa_canal_detecta_e_salva(monkeypatch, tmp_path):
    _patch_api(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_meu_canal("UC_X", _jogos(), destino, limite=2, limite_comentarios=10)

    assert resumo == {
        "analisados": 2,
        "jogos_detectados": 1,
        "jogos_nao_detectados": 1,
        "novos": 2,
        "atualizados": 0,
        "erros": 0,
    }
    linhas = _ler_linhas(destino)
    por_id = {linha["video_id"]: linha for linha in linhas}
    assert por_id["VID0"]["jogo_detectado"] == "Resident Evil"
    assert por_id["VID1"]["jogo_detectado"] == ""


def test_segunda_passada_atualiza_sem_duplicar(monkeypatch, tmp_path):
    _patch_api(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    analisar_meu_canal("UC_X", _jogos(), destino, limite=2)
    resumo = analisar_meu_canal("UC_X", _jogos(), destino, limite=2)

    assert resumo["novos"] == 0
    assert resumo["atualizados"] == 2
    assert len(_ler_linhas(destino)) == 2


def test_erro_de_comentarios_nao_derruba_video(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)

    def _boom(url, timeout=10):
        corpo = json.dumps({"error": {"errors": [{"reason": "quotaExceeded"}]}}).encode("utf-8")
        raise HTTPError("u", 403, "Forbidden", {}, io.BytesIO(corpo))

    monkeypatch.setattr(coletor_youtube, "urlopen", _boom)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_meu_canal("UC_X", _jogos(), destino, limite=1)

    assert resumo["analisados"] == 1
    assert resumo["erros"] == 0


def test_timeout_de_comentarios_nao_interrompe_e_marca_incompleto(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json)

    def _timeout(url, timeout=10):
        raise TimeoutError("tempo esgotado")

    monkeypatch.setattr(coletor_youtube, "urlopen", _timeout)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_meu_canal("UC_X", _jogos(), destino, limite=1)

    linhas = _ler_linhas(destino)
    assert resumo["analisados"] == 1
    assert resumo["erros"] == 0
    assert linhas[0]["comentarios_incompletos"] == "sim"
    saida = capsys.readouterr().out
    assert "VID0" in saida
    assert "comentarios" in saida
    assert "continuara" in saida


# --- CLI: ausencia de chave/canal vira mensagem clara, sem tocar a rede ---

def test_cli_sem_chave_mostra_mensagem(monkeypatch, capsys):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)

    coletar_meu_canal_interativo(5, 20)

    assert "YOUTUBE_API_KEY" in capsys.readouterr().out


def test_cli_sem_canal_mostra_mensagem(monkeypatch, capsys):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)

    coletar_meu_canal_interativo(5, 20)

    assert "MEU_CANAL_YOUTUBE_ID" in capsys.readouterr().out


# --- Coleta completa inteligente (Sprint 10.9): paginacao + lote + estrategia de comentarios ---

# channels -> uploads; playlistItems pagina (VID0,VID1 | VID2); videos.list em lote.
# VID0 cita o jogo na descricao (detecta por metadado, sem comentarios); VID1 nao tem
# nada no metadado (precisa de comentarios); VID2 nao tem o jogo em lugar nenhum.
def _fake_get_json_completo(url):
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
                        "title": f"meu video {vid}",
                        "channelTitle": "Meu Canal",
                        "description": "Jogo: Resident Evil" if vid == "VID0" else "",
                        "tags": [],
                        "publishedAt": "2026-06-10T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": "PT5M"},
                }
                for vid in ids
            ]
        }
    return {"items": []}


# commentThreads: VID1 tem o jogo nos comentarios; os demais nao.
class _RespostaComentariosVideo:
    def __init__(self, video_id):
        self.video_id = video_id

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        textos = ["amei resident evil"] if self.video_id == "VID1" else ["video muito legal"]
        return json.dumps(
            {
                "items": [
                    {"snippet": {"topLevelComment": {"snippet": {"textDisplay": t}}}}
                    for t in textos
                ]
            }
        )


def _fake_urlopen_por_video(url, timeout=10):
    video_id = parse_qs(urlparse(url).query)["videoId"][0]
    return _RespostaComentariosVideo(video_id)


def _patch_completo(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_completo)
    monkeypatch.setattr(coletor_youtube, "urlopen", _fake_urlopen_por_video)


def test_analisar_canal_completo_estrategia_de_deteccao(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_canal_completo("UC_X", _jogos(), destino, set(), None, 10, 50)

    assert resumo == {
        "encontrados": 3,
        "em_cache": 0,
        "analisados": 3,
        "detectados_sem_comentarios": 1,  # VID0 pela descricao
        "detectados_por_comentarios": 1,  # VID1 pelos comentarios
        "sem_jogo": 1,                    # VID2
        "erros": 0,
    }
    assert len(_ler_linhas(destino)) == 3


def test_analisar_canal_completo_pula_videos_em_cache(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_canal_completo("UC_X", _jogos(), destino, {"VID0", "VID1"}, None, 10, 0)

    assert resumo["encontrados"] == 3
    assert resumo["em_cache"] == 2
    assert resumo["analisados"] == 1  # so VID2
    assert resumo["sem_jogo"] == 1


def test_analisar_canal_completo_respeita_teto(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_canal_completo("UC_X", _jogos(), destino, set(), 2, 10, 0)

    assert resumo["encontrados"] == 2  # so VID0 e VID1 (primeira pagina, teto atingido)
    assert resumo["analisados"] == 2


def test_analisar_canal_completo_nao_busca_comentarios_quando_metadado_basta(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    # Todos os videos citam o jogo na descricao -> deteccao por metadado, sem comentarios.
    def _todos_por_metadado(url):
        if "/videos" in url:
            ids = parse_qs(urlparse(url).query)["id"][0].split(",")
            return {
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "title": f"video {vid}",
                            "channelTitle": "Meu Canal",
                            "description": "Jogo: Resident Evil",
                            "tags": [],
                            "publishedAt": "2026-06-10T00:00:00Z",
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                        "contentDetails": {"duration": "PT2M"},
                    }
                    for vid in ids
                ]
            }
        return _fake_get_json_completo(url)

    def _urlopen_proibido(url, timeout=10):
        raise AssertionError("comentarios nao deveriam ser buscados quando o metadado detecta")

    monkeypatch.setattr(coletor_youtube, "_get_json", _todos_por_metadado)
    monkeypatch.setattr(coletor_youtube, "urlopen", _urlopen_proibido)

    resumo = analisar_canal_completo("UC_X", _jogos(), tmp_path / "m.csv", set(), None, 20, 100)

    assert resumo["detectados_sem_comentarios"] == 3
    assert resumo["detectados_por_comentarios"] == 0
    assert resumo["sem_jogo"] == 0


def test_analisar_canal_completo_salva_parcial_apos_lote_com_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _fake_get_json_timeout_no_segundo_lote(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        if "/playlistItems" in url:
            return {
                "items": [
                    {"contentDetails": {"videoId": f"VID{i}"}}
                    for i in range(51)
                ]
            }
        if "/videos" in url:
            ids = parse_qs(urlparse(url).query)["id"][0].split(",")
            if ids == ["VID50"]:
                raise TimeoutError("tempo esgotado")
            return {
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "title": f"video {vid}",
                            "channelTitle": "Meu Canal",
                            "description": "Jogo: Resident Evil",
                            "tags": [],
                            "publishedAt": "2026-06-10T00:00:00Z",
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                        "contentDetails": {"duration": "PT2M"},
                    }
                    for vid in ids
                ]
            }
        return {"items": []}

    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_timeout_no_segundo_lote)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_canal_completo("UC_X", _jogos(), destino, set(), None, 0, 0)

    assert resumo["encontrados"] == 51
    assert resumo["analisados"] == 50
    assert resumo["erros"] == 1
    assert len(_ler_linhas(destino)) == 50


def test_analisar_canal_completo_todos_videos_nao_para_em_20_ou_50(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")

    def _fake_get_json_120(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        if "/playlistItems" in url:
            token = parse_qs(urlparse(url).query).get("pageToken", [None])[0]
            inicio = 0 if token is None else int(token)
            fim = min(inicio + 50, 120)
            payload = {
                "items": [
                    {"contentDetails": {"videoId": f"VID{i}"}}
                    for i in range(inicio, fim)
                ]
            }
            if fim < 120:
                payload["nextPageToken"] = str(fim)
            return payload
        if "/videos" in url:
            ids = parse_qs(urlparse(url).query)["id"][0].split(",")
            return {
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "title": f"video {vid}",
                            "channelTitle": "Meu Canal",
                            "description": "Jogo: Resident Evil",
                            "tags": [],
                            "publishedAt": "2026-06-10T00:00:00Z",
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                        "contentDetails": {"duration": "PT2M"},
                    }
                    for vid in ids
                ]
            }
        return {"items": []}

    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_get_json_120)

    resumo = analisar_canal_completo("UC_X", _jogos(), tmp_path / "meus_videos.csv", set(), None, 0, 0)

    assert resumo["encontrados"] == 120
    assert resumo["analisados"] == 120


def test_cli_diagnosticar_meu_video_mostra_campos_relevantes(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(main_mod, "DATA_DIR", tmp_path)
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nResident Evil,resident evil|re4,terror,8\n",
        encoding="utf-8",
    )

    def _fake_detalhe(video_id):
        from modelos import DetalheVideoYoutube

        return DetalheVideoYoutube(
            video_id=video_id,
            titulo="Video diagnosticado",
            descricao="Jogo: Dark Hours\nDescricao longa para teste.",
            tags=["dark hours", "gameplay"],
            url=f"https://www.youtube.com/watch?v={video_id}",
            views=100,
            likes=10,
            comentarios=3,
            data_publicacao="2026-07-01",
            duracao_segundos=120,
            tipo_video="longo",
        )

    def _fake_comentarios(video_id, limite=50):
        return SimpleNamespace(
            textos=["comentario principal", "resposta com contexto"],
            comentarios_principais=1,
            respostas=1,
            incompleto=False,
        )

    monkeypatch.setattr(main_mod, "coletar_detalhe_video", _fake_detalhe, raising=False)
    monkeypatch.setattr(main_mod, "coletar_textos_comentarios", _fake_comentarios, raising=False)

    assert main_mod.main(["diagnosticar_meu_video", "VID_DIAG"]) == 0

    saida = capsys.readouterr().out
    assert "Video diagnosticado" in saida
    assert "Descricao coletada: sim" in saida
    assert "Tags coletadas: 2" in saida
    assert "Jogo detectado: Dark Hours" in saida
    assert "Fonte da deteccao: descricao" in saida
    assert "Confianca: alta" in saida
    assert "fora do seed" in saida
    assert "CHAVE_FAKE" not in saida


# --- Recoleta forcada: o cache de ids_existentes precisa de valvula de escape ---
#
# Regressao: videos salvos antes da coluna descricao existir ficavam presos. A migracao
# arruma o cabecalho, mas so uma nova coleta preenche a linha — e a coleta completa
# pulava justamente quem ja estava no CSV. Com --forcar o video volta a ser analisado.

def test_analisar_canal_completo_forcar_reanalisa_videos_em_cache(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    destino = tmp_path / "meus_videos.csv"

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), destino, {"VID0", "VID1"}, None, 10, 0, forcar=True
    )

    assert resumo["encontrados"] == 3
    assert resumo["em_cache"] == 0
    assert resumo["analisados"] == 3


def test_analisar_canal_completo_forcar_preenche_linha_antiga_sem_descricao(
    monkeypatch, tmp_path
):
    _patch_completo(monkeypatch)
    destino = tmp_path / "meus_videos.csv"
    # Linha no formato antigo: sem descricao, sem tags e sem jogo detectado.
    salvar_meu_video(
        destino,
        MeuVideo(
            video_id="VID0",
            titulo="meu video VID0",
            url="https://y/VID0",
            data_publicacao="2026-06-10",
            jogo_detectado="",
            confianca_jogo="nao_detectado",
            fonte_deteccao="nao_detectado",
            views=1000,
            likes=100,
            comentarios=10,
            descricao="",
            tags=[],
        ),
    )

    analisar_canal_completo("UC_X", _jogos(), destino, {"VID0"}, None, 10, 0, forcar=True)

    linha = next(l for l in _ler_linhas(destino) if l["video_id"] == "VID0")
    assert linha["descricao"] == "Jogo: Resident Evil"
    assert linha["jogo_detectado"] == "Resident Evil"


# --- Validade do checkpoint de ids: cache sem expiracao esconde upload novo ---
#
# O checkpoint existe para retomar uma coleta interrompida sem repaginar a playlist.
# Sem validade ele congela a lista de ids: todo video publicado depois fica invisivel,
# por mais que a coleta rode. O campo salvo_em ja era gravado — so nunca era lido.

def _escrever_checkpoint(caminho, ids, salvo_em, channel_id="UC_X", limite_maximo=None):
    dados = {
        "channel_id": channel_id,
        "limite_maximo": limite_maximo,
        "video_ids": ids,
        "total": len(ids),
    }
    if salvo_em is not None:
        dados["salvo_em"] = salvo_em
    caminho.write_text(json.dumps(dados), encoding="utf-8")


def _agora_menos(horas):
    return (datetime.now() - timedelta(hours=horas)).isoformat(timespec="seconds")


def test_checkpoint_recente_evita_repaginar_o_canal(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    # A playlist fake tem 3 videos; o checkpoint tem 1. Se o checkpoint for usado,
    # "encontrados" fica em 1 — nao ha como confundir com a paginacao.
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], _agora_menos(1))

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        caminho_checkpoint=checkpoint,
    )

    assert resumo["encontrados"] == 1


def test_checkpoint_vencido_repagina_o_canal(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], _agora_menos(7))

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        caminho_checkpoint=checkpoint,
    )

    assert resumo["encontrados"] == 3


def test_checkpoint_sem_data_e_descartado(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], None)

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        caminho_checkpoint=checkpoint,
    )

    assert resumo["encontrados"] == 3


def test_checkpoint_com_data_invalida_e_descartado(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], "ontem de manha")

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        caminho_checkpoint=checkpoint,
    )

    assert resumo["encontrados"] == 3


def test_forcar_ignora_checkpoint_ainda_valido(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], _agora_menos(1))

    resumo = analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        forcar=True,
        caminho_checkpoint=checkpoint,
    )

    assert resumo["encontrados"] == 3


def test_repaginar_regrava_o_checkpoint_com_data_nova(monkeypatch, tmp_path):
    _patch_completo(monkeypatch)
    checkpoint = tmp_path / "ck.json"
    _escrever_checkpoint(checkpoint, ["VID_DO_CHECKPOINT"], _agora_menos(7))

    analisar_canal_completo(
        "UC_X", _jogos(), tmp_path / "m.csv", set(), None, 0, 0,
        caminho_checkpoint=checkpoint,
    )

    dados = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert dados["video_ids"] == ["VID0", "VID1", "VID2"]
    assert datetime.fromisoformat(dados["salvo_em"]) > datetime.now() - timedelta(minutes=5)
