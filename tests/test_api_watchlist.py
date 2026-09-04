import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def test_watchlist_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WATCHLIST_CSV", tmp_path / "watchlist.csv")

    resposta = client.get("/watchlist")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_watchlist_lista_jogos_adicionados(tmp_path, monkeypatch):
    caminho = tmp_path / "watchlist.csv"
    caminho.write_text(
        "nome_jogo,data_adicao\nRepo,2026-05-01 10:00:00\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "WATCHLIST_CSV", caminho)

    resposta = client.get("/watchlist")

    assert resposta.json() == ["Repo"]


def test_watchlist_ranking_marca_jogo_fora_do_ranking(tmp_path, monkeypatch):
    caminho = tmp_path / "watchlist.csv"
    caminho.write_text(
        "nome_jogo,data_adicao\nJogoFantasma,2026-05-01 10:00:00\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "WATCHLIST_CSV", caminho)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    resposta = client.get("/watchlist/ranking")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo[0]["nome"] == "JogoFantasma"
    assert corpo[0]["posicao"] is None
