import io
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import coletor_youtube
from analise_meu_canal import analisar_meu_canal
from leitor_csv import _ler_linhas
from main import coletar_meu_canal_interativo
from modelos import JogoSeed


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
