import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leitor_csv import _ler_linhas
from meus_videos import (
    CAMPOS_MEU_VIDEO,
    calcular_score_resultado_real,
    salvar_meu_video,
)
from modelos import MeuVideo


def _meu_video(
    video_id="vid1",
    views=500000,
    likes=40000,
    comentarios=2000,
    status_analise="pendente",
) -> MeuVideo:
    return MeuVideo(
        video_id=video_id,
        titulo="Joguei o jogo de terror mais pesado do ano",
        url=f"https://www.youtube.com/watch?v={video_id}",
        data_publicacao="2026-06-10",
        jogo_detectado="Resident Evil",
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video="longo",
        status_analise=status_analise,
    )


def test_cria_csv_com_cabecalho_e_salva_video(tmp_path):
    caminho = tmp_path / "meus_videos.csv"

    resultado = salvar_meu_video(caminho, _meu_video(), data_coleta="2026-06-17")

    assert resultado == "criado"
    linhas = _ler_linhas(caminho)
    assert len(linhas) == 1
    assert list(linhas[0].keys()) == CAMPOS_MEU_VIDEO
    assert linhas[0]["video_id"] == "vid1"
    assert linhas[0]["data_coleta"] == "2026-06-17"
    assert linhas[0]["jogo_detectado"] == "Resident Evil"


def test_atualiza_video_existente_sem_duplicar(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(views=100000), data_coleta="2026-06-15")

    resultado = salvar_meu_video(
        caminho,
        _meu_video(views=900000, likes=80000, comentarios=5000),
        data_coleta="2026-06-17",
    )

    assert resultado == "atualizado"
    linhas = _ler_linhas(caminho)
    assert len(linhas) == 1
    assert linhas[0]["views"] == "900000"
    assert linhas[0]["likes"] == "80000"
    assert linhas[0]["comentarios"] == "5000"
    assert linhas[0]["data_coleta"] == "2026-06-17"


def test_update_preserva_status_analise(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(status_analise="analisado"), data_coleta="2026-06-15")

    # Recoletar manda status "pendente", mas o ja registrado deve ser preservado.
    salvar_meu_video(caminho, _meu_video(views=999, status_analise="pendente"), data_coleta="2026-06-17")

    linhas = _ler_linhas(caminho)
    assert linhas[0]["status_analise"] == "analisado"


def test_score_resultado_real_reflete_metricas(tmp_path):
    fraco = calcular_score_resultado_real(_meu_video(views=1000, likes=10, comentarios=1))
    forte = calcular_score_resultado_real(
        _meu_video(views=2000000, likes=200000, comentarios=10000)
    )

    assert 0 <= fraco < forte <= 100


def test_score_salvo_no_csv(tmp_path):
    caminho = tmp_path / "meus_videos.csv"

    salvar_meu_video(caminho, _meu_video(), data_coleta="2026-06-17")

    linhas = _ler_linhas(caminho)
    assert float(linhas[0]["score_resultado_real"]) > 0
