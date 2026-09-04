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
