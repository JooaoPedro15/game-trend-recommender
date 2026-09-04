import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def test_status(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", tmp_path / "videos.csv")
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")
    monkeypatch.setattr(config, "HISTORICO_CSV", tmp_path / "historico.csv")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")

    resposta = client.get("/status")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["videos_coletados"] == 0
    assert corpo["chave_configurada"] in {True, False}


def test_status_arquivo_ilegivel_devolve_503(tmp_path, monkeypatch):
    caminho = tmp_path / "videos.csv"
    # bytes invalidos em UTF-8 (encoding usado por _ler_linhas): dispara UnicodeDecodeError
    # de verdade na leitura, sem depender de permissao de arquivo (que o Windows nao
    # restringe do mesmo jeito que um diretorio vazio: st_size==0 tambem para diretorio,
    # entao _ler_linhas nunca chegaria a abrir o arquivo se usassemos um diretorio aqui).
    caminho.write_bytes(b"titulo,canal\n\xff\xfeinvalido\n")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", caminho)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", tmp_path / "meus_videos.csv")
    monkeypatch.setattr(config, "HISTORICO_CSV", tmp_path / "historico.csv")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")

    resposta = client.get("/status")

    assert resposta.status_code == 503


def test_historico_comparacao_sem_dados_devolve_409(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "HISTORICO_CSV", tmp_path / "historico.csv")

    resposta = client.get("/historico/comparacao")

    assert resposta.status_code == 409


def test_historico_comparacao_com_duas_execucoes(tmp_path, monkeypatch):
    caminho = tmp_path / "historico.csv"
    caminho.write_text(
        "data_execucao,posicao,nome_jogo,score_final,score_tendencia,score_fit_canal,"
        "score_descoberta,score_saturacao,score_oportunidade,videos_encontrados,"
        "canais_diferentes,acao_recomendada,motivo\n"
        "2026-05-01 10:00:00,1,Repo,70,70,70,10,90,60,1,1,Testar,motivo\n"
        "2026-05-02 10:00:00,1,Repo,80,80,70,10,90,70,1,1,Testar,motivo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "HISTORICO_CSV", caminho)

    resposta = client.get("/historico/comparacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["data_atual"] == "2026-05-02 10:00:00"
