import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

import config
from api.main import app

client = TestClient(app)


def _preparar_meus_videos(tmp_path, monkeypatch):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,500000,20000,5000,2026-05-01,\n",
        encoding="utf-8",
    )
    meus_videos_csv = tmp_path / "meus_videos.csv"
    meus_videos_csv.write_text(
        "video_id,data_coleta,data_publicacao,titulo,jogo_detectado,confianca_jogo,"
        "fonte_deteccao,url,views,likes,comentarios,tipo_video,score_resultado_real,status_analise\n"
        "vid1,2026-05-02,2026-05-01,Meu video sem jogo,,,,https://y/m1,100,1,0,curto,10,pendente\n"
        "vid2,2026-05-02,2026-05-01,Meu video do Repo,Repo,alta,descricao,https://y/m2,"
        "600000,30000,6000,curto,90,pendente\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "VIDEOS_CSV", videos_csv)
    monkeypatch.setattr(config, "MEUS_VIDEOS_CSV", meus_videos_csv)


def test_meu_canal_sem_jogo(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    resposta = client.get("/meu-canal/sem-jogo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["titulo"] == "Meu video sem jogo"
    assert "sugestao" in corpo[0]


def test_meu_canal_comparacao(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    resposta = client.get("/meu-canal/comparacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo[0]["jogo"] == "Repo"
    assert corpo[0]["conclusao"] in {
        "ainda_nao_testado", "recomendacao_confirmada", "prometia_mas_nao_funcionou",
        "funcionou_melhor_que_o_esperado", "precisa_de_mais_testes",
    }


def test_meu_canal_repetir_e_falhos_respondem_200(tmp_path, monkeypatch):
    _preparar_meus_videos(tmp_path, monkeypatch)

    assert client.get("/meu-canal/repetir").status_code == 200
    assert client.get("/meu-canal/falhos").status_code == 200
