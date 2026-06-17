import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fit_canal import agrupar_meus_videos_por_jogo, calcular_fit_real_jogo
from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo


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
