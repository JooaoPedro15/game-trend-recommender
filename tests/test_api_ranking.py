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
