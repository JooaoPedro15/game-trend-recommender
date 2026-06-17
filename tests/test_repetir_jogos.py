import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, MeuVideo, ResultadoRecomendacao
from repetir_jogos import jogos_para_repetir


# Recomendacao fake: so oportunidade e saturacao importam para os criterios; resto e padrao.
def _rec(nome, score_oportunidade, score_saturacao):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=8.0),
        score_final=0.0,
        score_tendencia=0.0,
        score_fit_canal=0.0,
        score_descoberta=0.0,
        score_saturacao=score_saturacao,
        videos_encontrados=0,
        canais_diferentes=0,
        motivo="",
        videos=[],
        score_oportunidade=score_oportunidade,
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


def test_inclui_jogo_que_funcionou_com_janela_aberta():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=75)]
    meus = [_forte("RE", "a", tipo="curto")]

    candidatos = jogos_para_repetir(ranking, meus)

    assert len(candidatos) == 1
    candidato = candidatos[0]
    assert candidato.jogo == "RE"
    assert candidato.score_resultado_real >= 60.0
    assert candidato.tipo_video == "curto"
    assert candidato.melhor_video_url == "https://youtu.be/a"
    assert candidato.motivo


def test_exclui_jogo_que_nao_funcionou_comigo():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=75)]
    meus = [_fraco("RE", "a")]  # resultado real baixo

    assert jogos_para_repetir(ranking, meus) == []


def test_exclui_jogo_com_janela_fechada():
    ranking = [_rec("RE", score_oportunidade=30, score_saturacao=75)]  # oportunidade baixa
    meus = [_forte("RE", "a")]

    assert jogos_para_repetir(ranking, meus) == []


def test_exclui_jogo_saturado_demais():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=30)]  # saturado
    meus = [_forte("RE", "a")]

    assert jogos_para_repetir(ranking, meus) == []


def test_exclui_jogo_sem_historico_no_meu_canal():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=75)]
    meus = [_forte("Outro", "a")]  # nenhum video de RE

    assert jogos_para_repetir(ranking, meus) == []


def test_usa_o_melhor_video_do_jogo():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=75)]
    meus = [_fraco("RE", "ruim"), _forte("RE", "bom", tipo="longo")]

    candidato = jogos_para_repetir(ranking, meus)[0]

    assert candidato.melhor_video_titulo == "video bom"
    assert candidato.tipo_video == "longo"


def test_exclui_resultado_mediano_abaixo_do_limiar():
    ranking = [_rec("RE", score_oportunidade=70, score_saturacao=75)]
    meus = [_meu("RE", "re", 900000, 44000, 1000)]  # ~51, abaixo de RESULTADO_BOM (60)

    assert jogos_para_repetir(ranking, meus) == []


def test_ordena_por_resultado_real_desc():
    ranking = [
        _rec("RE", score_oportunidade=70, score_saturacao=75),
        _rec("LC", score_oportunidade=70, score_saturacao=75),
    ]
    meus = [
        _forte("LC", "lc"),                            # ~66
        _meu("RE", "re", 2000000, 300000, 20000),      # ~70 (maior)
    ]

    candidatos = jogos_para_repetir(ranking, meus)

    assert [c.jogo for c in candidatos] == ["RE", "LC"]
