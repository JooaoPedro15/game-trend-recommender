import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import metricas_video
from modelos import VideoColetado


def _video(views=100000, data_publicacao=None):
    return VideoColetado(
        titulo="Video teste",
        canal="Canal Teste",
        plataforma="youtube",
        url="https://youtube.com/watch?v=teste",
        views=views,
        likes=0,
        comentarios=0,
        data_publicacao=data_publicacao or date.today().isoformat(),
        texto_comentarios="",
    )


def test_views_por_dia_divide_views_pela_idade_do_video():
    dois_dias_atras = (date.today() - timedelta(days=2)).isoformat()
    video = _video(views=100000, data_publicacao=dois_dias_atras)

    assert metricas_video.views_por_dia(video) == 50000.0


def test_views_por_dia_usa_idade_minima_de_um_dia_para_video_publicado_hoje():
    video = _video(views=25000, data_publicacao=date.today().isoformat())

    assert metricas_video.views_por_dia(video) == 25000.0


def test_views_por_dia_retorna_zero_quando_data_publicacao_e_invalida():
    video = _video(views=100000, data_publicacao="data-invalida")

    assert metricas_video.views_por_dia(video) == 0.0
