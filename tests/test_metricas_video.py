import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import metricas_video
from modelos import VideoColetado


def _video(views=100000, data_publicacao=None, likes=0, comentarios=0):
    return VideoColetado(
        titulo="Video teste",
        canal="Canal Teste",
        plataforma="youtube",
        url="https://youtube.com/watch?v=teste",
        views=views,
        likes=likes,
        comentarios=comentarios,
        data_publicacao=data_publicacao or date.today().isoformat(),
        texto_comentarios="",
    )


def test_views_por_dia_divide_views_pela_idade_do_video():
    dois_dias_atras = (date.today() - timedelta(days=2)).isoformat()
    video = _video(views=100000, data_publicacao=dois_dias_atras)

    assert metricas_video.calcular_views_por_dia(video) == 50000.0


def test_views_por_dia_usa_idade_minima_de_um_dia_para_video_publicado_hoje():
    video = _video(views=25000, data_publicacao=date.today().isoformat())

    assert metricas_video.calcular_views_por_dia(video) == 25000.0


def test_views_por_dia_retorna_zero_quando_data_publicacao_e_invalida():
    video = _video(views=100000, data_publicacao="data-invalida")

    assert metricas_video.calcular_views_por_dia(video) == 0.0


def test_views_por_dia_mantem_alias_compativel():
    dois_dias_atras = (date.today() - timedelta(days=2)).isoformat()
    video = _video(views=100000, data_publicacao=dois_dias_atras)

    assert metricas_video.views_por_dia(video) == 50000.0


# --- Score de viralidade do video ---

def test_viralidade_baixa_performance_pontua_quase_zero():
    video = _video(views=1000, data_publicacao="2020-01-01", likes=0, comentarios=0)

    assert metricas_video.calcular_score_viralidade_video(video) < 5.0


def test_viralidade_alta_performance_chega_a_100():
    # 2M views hoje, taxa 11% -> volume, engajamento, velocidade e recencia no maximo
    video = _video(
        views=2_000_000, data_publicacao=date.today().isoformat(), likes=200_000, comentarios=20_000
    )

    assert metricas_video.calcular_score_viralidade_video(video) == 100.0


def test_viralidade_peso_do_canal_nao_ultrapassa_100():
    video = _video(
        views=2_000_000, data_publicacao=date.today().isoformat(), likes=200_000, comentarios=20_000
    )

    assert metricas_video.calcular_score_viralidade_video(video, peso_canal=2.0) == 100.0


def test_viralidade_alto_engajamento_satura_o_componente():
    # views baixas (volume pequeno) e data antiga (recencia 0), mas taxa altissima
    base = _video(views=50_000, data_publicacao="2020-01-01", likes=10_000, comentarios=5_000)  # 30%
    dobro = _video(views=50_000, data_publicacao="2020-01-01", likes=20_000, comentarios=10_000)  # 60%

    score_base = metricas_video.calcular_score_viralidade_video(base)
    assert 30.0 <= score_base < 40.0
    # passar do teto de engajamento (10%) nao muda nada: o componente esta saturado
    assert metricas_video.calcular_score_viralidade_video(dobro) == score_base


def test_viralidade_video_recente_pontua_mais_que_antigo():
    recente = _video(
        views=200_000, data_publicacao=date.today().isoformat(), likes=2_000, comentarios=200
    )
    antigo = _video(
        views=200_000,
        data_publicacao=(date.today() - timedelta(days=200)).isoformat(),
        likes=2_000,
        comentarios=200,
    )

    assert metricas_video.calcular_score_viralidade_video(recente) > metricas_video.calcular_score_viralidade_video(antigo)


def test_viralidade_fica_entre_0_e_100():
    videos = [
        _video(views=1000, data_publicacao="2020-01-01"),
        _video(
            views=5_000_000,
            data_publicacao=date.today().isoformat(),
            likes=1_000_000,
            comentarios=500_000,
        ),
    ]
    for video in videos:
        score = metricas_video.calcular_score_viralidade_video(video, peso_canal=3.0)
        assert 0.0 <= score <= 100.0
