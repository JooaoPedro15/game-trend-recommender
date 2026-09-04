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
