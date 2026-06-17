import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jogos_falhos import jogos_que_nao_funcionaram
from modelos import JogoSeed, MeuVideo, ResultadoRecomendacao


# Recomendacao fake: so nicho e oportunidade importam para os criterios; resto e padrao.
def _rec(nome, score_evidencia_nicho, score_oportunidade):
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
        score_oportunidade=score_oportunidade,
        score_evidencia_nicho=score_evidencia_nicho,
    )


# Meu video fake com data antiga: score_resultado_real deterministico. forte ~66, fraco ~4.
def _meu(jogo, video_id, views, likes, comentarios, tipo="curto"):
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


def _forte(jogo, video_id, tipo="curto"):
    return _meu(jogo, video_id, 900000, 120000, 8000, tipo)


def _fraco(jogo, video_id, tipo="curto"):
    return _meu(jogo, video_id, 80000, 200, 50, tipo)


def test_inclui_jogo_que_prometia_mas_falhou():
    ranking = [_rec("RE", score_evidencia_nicho=80, score_oportunidade=75)]
    meus = [_fraco("RE", "a", tipo="longo")]  # resultado real baixo

    falhos = jogos_que_nao_funcionaram(ranking, meus)

    assert len(falhos) == 1
    falho = falhos[0]
    assert falho.jogo == "RE"
    assert falho.score_resultado_real < 40.0
    assert falho.tipo_video == "longo"
    assert falho.melhor_video_url == "https://youtu.be/a"
    assert falho.conclusao


def test_exclui_jogo_que_funcionou_comigo():
    ranking = [_rec("RE", score_evidencia_nicho=80, score_oportunidade=75)]
    meus = [_forte("RE", "a")]  # resultado real alto

    assert jogos_que_nao_funcionaram(ranking, meus) == []


def test_exclui_jogo_sem_evidencia_de_nicho():
    ranking = [_rec("RE", score_evidencia_nicho=30, score_oportunidade=75)]  # nicho baixo
    meus = [_fraco("RE", "a")]

    assert jogos_que_nao_funcionaram(ranking, meus) == []


def test_exclui_jogo_sem_oportunidade_alta():
    ranking = [_rec("RE", score_evidencia_nicho=80, score_oportunidade=40)]  # oportunidade baixa
    meus = [_fraco("RE", "a")]

    assert jogos_que_nao_funcionaram(ranking, meus) == []


def test_exclui_jogo_sem_historico_no_meu_canal():
    ranking = [_rec("RE", score_evidencia_nicho=80, score_oportunidade=75)]
    meus = [_fraco("Outro", "a")]  # nenhum video de RE

    assert jogos_que_nao_funcionaram(ranking, meus) == []


def test_usa_o_melhor_video_e_ainda_assim_falha():
    ranking = [_rec("RE", score_evidencia_nicho=80, score_oportunidade=75)]
    # dois videos fracos; mesmo o "melhor" deles fica abaixo do corte
    meus = [_meu("RE", "pior", 10000, 5, 1), _fraco("RE", "melhor", tipo="curto")]

    falhos = jogos_que_nao_funcionaram(ranking, meus)

    assert len(falhos) == 1
    assert falhos[0].melhor_video_url == "https://youtu.be/melhor"


def test_ordena_pela_maior_promessa_externa():
    ranking = [
        _rec("RE", score_evidencia_nicho=80, score_oportunidade=65),
        _rec("LC", score_evidencia_nicho=80, score_oportunidade=90),
    ]
    meus = [_fraco("RE", "re"), _fraco("LC", "lc")]

    falhos = jogos_que_nao_funcionaram(ranking, meus)

    # maior oportunidade (promessa externa) primeiro
    assert [f.jogo for f in falhos] == ["LC", "RE"]
