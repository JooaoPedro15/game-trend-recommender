import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fit_canal import (
    agrupar_meus_videos_por_jogo,
    calcular_fit_real_jogo,
    desempenho_por_formato_do_jogo,
    sugerir_formato_por_historico,
)
from meus_videos import calcular_score_resultado_real
from modelos import JogoSeed, MeuVideo, ResultadoRecomendacao


# Data antiga zera recencia/velocidade: o score fica deterministico (volume + engajamento).
def _meu(jogo, video_id, views, likes, comentarios):
    return MeuVideo(
        video_id=video_id,
        titulo=f"video {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="media" if jogo else "nao_detectado",
        fonte_deteccao="titulo" if jogo else "nao_detectado",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video="longo",
    )


def _forte(jogo, video_id):
    return _meu(jogo, video_id, 900000, 120000, 8000)


def _fraco(jogo, video_id):
    return _meu(jogo, video_id, 80000, 200, 50)


def test_fit_real_e_a_media_dos_meus_videos_do_jogo():
    forte = _forte("RE", "a")
    fraco = _fraco("RE", "b")
    meus = [forte, fraco, _forte("LC", "c")]

    esperado = round(
        (calcular_score_resultado_real(forte) + calcular_score_resultado_real(fraco)) / 2, 1
    )
    assert calcular_fit_real_jogo("RE", meus) == esperado


def test_fit_real_de_um_video_e_o_proprio_score():
    forte = _forte("RE", "a")

    assert calcular_fit_real_jogo("RE", [forte]) == calcular_score_resultado_real(forte)


def test_fit_real_jogo_nunca_testado_retorna_none():
    assert calcular_fit_real_jogo("Inexistente", [_forte("RE", "a")]) is None


def test_fit_real_sem_videos_retorna_none():
    assert calcular_fit_real_jogo("RE", []) is None


def test_fit_real_ignora_maiusculas():
    assert calcular_fit_real_jogo("resident evil", [_forte("Resident Evil", "a")]) is not None


def test_agrupar_por_jogo_ignora_videos_sem_jogo():
    grupos = agrupar_meus_videos_por_jogo([_forte("RE", "a"), _forte("RE", "b"), _fraco("", "x")])

    assert list(grupos.keys()) == ["re"]
    assert len(grupos["re"]) == 2


# --- Sprint 9.3: formato calibrado pelo historico ---

def _meu_fmt(jogo, video_id, views, likes, comentarios, tipo):
    return MeuVideo(
        video_id=video_id,
        titulo=f"video {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="media",
        fonte_deteccao="titulo",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video=tipo,
    )


def _rec(nome, acao=""):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=8.0),
        score_final=0.0,
        score_tendencia=0.0,
        score_fit_canal=0.0,
        score_descoberta=0.0,
        score_saturacao=0.0,
        videos_encontrados=0,
        canais_diferentes=0,
        motivo="",
        videos=[],
        acao_recomendada=acao,
    )


def test_desempenho_por_formato_do_jogo_separa_por_tipo():
    meus = [
        _meu_fmt("RE", "a", 900000, 120000, 8000, "curto"),  # forte
        _meu_fmt("RE", "b", 80000, 200, 50, "longo"),        # fraco
    ]

    desempenho = desempenho_por_formato_do_jogo("RE", meus)

    assert set(desempenho.keys()) == {"curto", "longo"}
    assert desempenho["curto"] > desempenho["longo"]


def test_sugere_curto_quando_curto_funcionou_no_historico():
    meus = [_meu_fmt("RE", "a", 900000, 120000, 8000, "curto")]  # forte ~66
    rec = _rec("RE", acao="Priorizar para video longo")  # acao aponta longo

    assert sugerir_formato_por_historico(rec, meus) == "curto"  # historico vence


def test_sugere_longo_quando_longo_funcionou_no_historico():
    meus = [_meu_fmt("RE", "a", 900000, 120000, 8000, "longo")]
    rec = _rec("RE", acao="Testar em Short")

    assert sugerir_formato_por_historico(rec, meus) == "longo"


def test_escolhe_o_formato_de_melhor_media():
    meus = [
        _meu_fmt("RE", "a", 900000, 120000, 8000, "curto"),  # ~66
        _meu_fmt("RE", "b", 900000, 44000, 1000, "live"),    # ~51
    ]

    assert sugerir_formato_por_historico(_rec("RE"), meus) == "curto"


def test_sem_historico_mantem_formato_da_acao():
    assert sugerir_formato_por_historico(_rec("RE", "Priorizar para video longo"), []) == "longo"
    assert sugerir_formato_por_historico(_rec("RE", "Testar em Short"), []) == "curto"
    assert sugerir_formato_por_historico(_rec("RE", "Monitorar por mais alguns dias"), []) == ""


def test_historico_fraco_mantem_formato_da_acao():
    meus = [_meu_fmt("RE", "a", 80000, 200, 50, "curto")]  # fraco ~4, abaixo do limiar
    rec = _rec("RE", acao="Priorizar para video longo")

    assert sugerir_formato_por_historico(rec, meus) == "longo"
