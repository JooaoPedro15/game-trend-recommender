import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evidencias_jogo import (
    EvidenciaVideo,
    calcular_score_evidencia_criadores,
    resumir_evidencia_criadores,
)


# Cria uma EvidenciaVideo de teste com score/canal/tipo controlados.
def _ev(score, canal="Canal A", tipo="curto"):
    return EvidenciaVideo(
        canal=canal,
        plataforma="youtube",
        tipo_video=tipo,
        titulo="titulo",
        url="https://exemplo.com/v",
        views=1000,
        likes=10,
        comentarios=1,
        taxa_engajamento=1.0,
        views_por_dia=10.0,
        score_viralidade_video=score,
        data_publicacao="2026-05-01",
    )


def test_score_um_criador_so_e_menor_que_varios():
    um = [_ev(80, canal="Canal A", tipo="curto")]
    varios = [
        _ev(80, canal="Canal A", tipo="curto"),
        _ev(70, canal="Canal B", tipo="longo"),
        _ev(65, canal="Canal C", tipo="curto"),
    ]

    assert calcular_score_evidencia_criadores(um) < calcular_score_evidencia_criadores(varios)


def test_score_varios_criadores_soma_bonus_de_diversidade():
    # media 60, 3 canais, 2 videos bons (>=60), curto e longo bons
    evidencias = [
        _ev(70, canal="Canal A", tipo="curto"),
        _ev(60, canal="Canal B", tipo="longo"),
        _ev(50, canal="Canal C", tipo="curto"),
    ]
    # 60 + min(2*6,18)=12 + min(1*5,15)=5 + curto(6) + longo(6) = 89.0
    assert calcular_score_evidencia_criadores(evidencias) == 89.0


def test_score_varios_virais_satura_em_100():
    evidencias = [
        _ev(90, canal="Canal A", tipo="curto"),
        _ev(85, canal="Canal B", tipo="longo"),
        _ev(80, canal="Canal C", tipo="curto"),
        _ev(75, canal="Canal D", tipo="longo"),
    ]

    assert calcular_score_evidencia_criadores(evidencias) == 100.0


def test_score_videos_fracos_fica_baixo_mesmo_com_varios_canais():
    # 3 canais, mas nenhum video performa: diversidade nao salva performance fraca
    evidencias = [
        _ev(20, canal="Canal A", tipo="curto"),
        _ev(15, canal="Canal B", tipo="longo"),
        _ev(10, canal="Canal C", tipo="curto"),
    ]

    assert calcular_score_evidencia_criadores(evidencias) < 40.0


def test_score_lista_vazia_e_zero():
    assert calcular_score_evidencia_criadores([]) == 0.0


def test_resumo_descreve_criadores_e_formatos():
    evidencias = [
        _ev(70, canal="Canal A", tipo="curto"),
        _ev(65, canal="Canal B", tipo="longo"),
        _ev(40, canal="Canal C", tipo="curto"),
    ]

    resumo = resumir_evidencia_criadores(evidencias)

    assert "3 criador" in resumo
    assert "2 video(s) com alta performance" in resumo
    assert "curto" in resumo
    assert "longo" in resumo
    assert resumo.endswith(".")
