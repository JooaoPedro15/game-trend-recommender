import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config
from api import dependencies


def test_carregar_jogos_le_do_data_dir(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    jogos = dependencies.carregar_jogos()

    assert len(jogos) == 1
    assert jogos[0].nome == "Repo"


def test_carregar_jogos_arquivo_ausente_devolve_lista_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    assert dependencies.carregar_jogos() == []


def test_carregar_jogos_arquivo_ilegivel_levanta_503(tmp_path, monkeypatch):
    caminho = tmp_path / "jogos_seed.csv"
    # bytes invalidos em UTF-8 (encoding usado por _ler_linhas): dispara UnicodeDecodeError
    # de verdade na leitura, sem depender de permissao de arquivo (que o Windows nao
    # restringe do mesmo jeito que um diretorio vazio: st_size==0 tambem para diretorio,
    # entao _ler_linhas nunca chegaria a abrir o arquivo se usassemos um diretorio aqui).
    caminho.write_bytes(b"nome,aliases,genero,fit_inicial\n\xff\xfeinvalido\n")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    with pytest.raises(Exception) as excinfo:
        dependencies.carregar_jogos()
    assert getattr(excinfo.value, "status_code", None) == 503


def test_carregar_ranking_delega_para_ranking_service(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,1000,10,1,2026-05-01,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")

    ranking = dependencies.carregar_ranking()

    assert len(ranking) == 1
    assert ranking[0].jogo.nome == "Repo"
