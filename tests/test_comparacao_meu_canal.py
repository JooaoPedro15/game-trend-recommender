import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comparacao_meu_canal import comparar_recomendacoes_com_meu_canal
from modelos import JogoSeed, MeuVideo, ResultadoRecomendacao


# Recomendacao fake: so os campos que a comparacao usa importam; o resto recebe padrao.
def _rec(nome, score_final, score_oportunidade=0.0, score_evidencia_nicho=0.0):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=0.5),
        score_final=score_final,
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


# Meu video fake. Data antiga zera recencia/velocidade do score: assim o resultado real
# fica deterministico (volume + engajamento), sem depender da data de hoje.
def _meu(jogo, video_id, views, likes, comentarios):
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
        tipo_video="longo",
    )


# Atalhos de resultado real: forte (~66), medio (~51), fraco (~4).
def _video_forte(jogo, video_id="forte"):
    return _meu(jogo, video_id, views=900000, likes=120000, comentarios=8000)


def _video_medio(jogo, video_id="medio"):
    return _meu(jogo, video_id, views=900000, likes=44000, comentarios=1000)


def _video_fraco(jogo, video_id="fraco"):
    return _meu(jogo, video_id, views=80000, likes=200, comentarios=50)


def test_ainda_nao_testado_sem_video_do_jogo():
    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 80)], [])

    assert comps[0].conclusao == "ainda_nao_testado"
    assert comps[0].score_resultado_real == 0.0
    assert comps[0].melhor_video_titulo == ""


def test_recomendacao_confirmada_aposta_alta_e_funcionou():
    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 80)], [_video_forte("Jogo A")])

    assert comps[0].conclusao == "recomendacao_confirmada"
    assert comps[0].score_resultado_real >= 60.0


def test_prometia_mas_nao_funcionou_aposta_alta_resultado_fraco():
    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 80)], [_video_fraco("Jogo A")])

    assert comps[0].conclusao == "prometia_mas_nao_funcionou"


def test_funcionou_melhor_que_o_esperado_aposta_baixa_resultado_forte():
    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 30)], [_video_forte("Jogo A")])

    assert comps[0].conclusao == "funcionou_melhor_que_o_esperado"


def test_precisa_de_mais_testes_zona_cinzenta():
    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 80)], [_video_medio("Jogo A")])

    assert comps[0].conclusao == "precisa_de_mais_testes"


def test_escolhe_o_melhor_video_do_jogo():
    meus = [_video_fraco("Jogo A", "ruim"), _video_forte("Jogo A", "bom")]

    comps = comparar_recomendacoes_com_meu_canal([_rec("Jogo A", 80)], meus)

    assert comps[0].melhor_video_titulo == "video bom"
    assert comps[0].conclusao == "recomendacao_confirmada"


def test_cruza_por_jogo_ignorando_maiusculas():
    comps = comparar_recomendacoes_com_meu_canal(
        [_rec("Resident Evil", 80)], [_video_forte("resident evil")]
    )

    assert comps[0].conclusao == "recomendacao_confirmada"
