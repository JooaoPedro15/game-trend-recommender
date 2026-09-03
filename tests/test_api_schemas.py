import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, ResultadoRecomendacao
from api.schemas import RankingItemOut


def test_ranking_item_out_aceita_campos_manuais():
    jogo = JogoSeed(nome="Repo", aliases=["repo"], genero="terror", fit_inicial=8)
    resultado = ResultadoRecomendacao(
        jogo=jogo, score_final=80.0, score_tendencia=70.0, score_fit_canal=80.0,
        score_descoberta=10.0, score_saturacao=90.0, videos_encontrados=1,
        canais_diferentes=1, motivo="motivo", videos=[],
    )
    item = RankingItemOut(
        posicao=1, jogo=resultado.jogo.nome, score_final=resultado.score_final,
        score_tendencia=resultado.score_tendencia, score_fit_canal=resultado.score_fit_canal,
        score_fit_real=resultado.score_fit_real, formato_sugerido=resultado.formato_sugerido,
        score_descoberta=resultado.score_descoberta, score_saturacao=resultado.score_saturacao,
        score_oportunidade=resultado.score_oportunidade,
        score_evidencia_criadores=resultado.score_evidencia_criadores,
        score_evidencia_nicho=resultado.score_evidencia_nicho,
        videos_encontrados=resultado.videos_encontrados,
        canais_diferentes=resultado.canais_diferentes, motivo=resultado.motivo,
        acao_recomendada=resultado.acao_recomendada, videos=[],
    )
    assert item.jogo == "Repo"
    assert item.model_dump()["score_final"] == 80.0
