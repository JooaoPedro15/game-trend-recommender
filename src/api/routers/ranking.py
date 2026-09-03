from datetime import date

from fastapi import APIRouter, Query

from api import dependencies
from api.schemas import OportunidadeOut, RankingItemOut, RankingVideoOut
from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia
from ranker import filtrar_oportunidades

router = APIRouter(tags=["ranking"])


def _video_out(video) -> RankingVideoOut:
    return RankingVideoOut(
        titulo=video.titulo,
        canal=video.canal,
        plataforma=video.plataforma,
        url=video.url,
        views=video.views,
        likes=video.likes,
        comentarios=video.comentarios,
        data_publicacao=video.data_publicacao,
        taxa_engajamento=round(calcular_taxa_engajamento(video) * 100, 1),
        views_por_dia=round(calcular_views_por_dia(video), 1),
    )


def _item_out(posicao: int, resultado) -> RankingItemOut:
    return RankingItemOut(
        posicao=posicao,
        jogo=resultado.jogo.nome,
        score_final=resultado.score_final,
        score_tendencia=resultado.score_tendencia,
        score_fit_canal=resultado.score_fit_canal,
        score_fit_real=resultado.score_fit_real,
        formato_sugerido=resultado.formato_sugerido,
        score_descoberta=resultado.score_descoberta,
        score_saturacao=resultado.score_saturacao,
        score_oportunidade=resultado.score_oportunidade,
        score_evidencia_criadores=resultado.score_evidencia_criadores,
        score_evidencia_nicho=resultado.score_evidencia_nicho,
        videos_encontrados=resultado.videos_encontrados,
        canais_diferentes=resultado.canais_diferentes,
        motivo=resultado.motivo,
        acao_recomendada=resultado.acao_recomendada,
        videos=[_video_out(video) for video in resultado.videos],
    )


@router.get("/ranking", response_model=list[RankingItemOut])
def obter_ranking(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    ranking = dependencies.carregar_ranking(plataforma, top, desde)
    return [_item_out(posicao, resultado) for posicao, resultado in enumerate(ranking, start=1)]


@router.get("/oportunidades", response_model=list[OportunidadeOut])
def obter_oportunidades(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    ranking = dependencies.carregar_ranking(plataforma, top, desde)
    oportunidades = filtrar_oportunidades(ranking)
    return [
        OportunidadeOut(
            posicao=posicao,
            jogo=resultado.jogo.nome,
            score_final=resultado.score_final,
            score_oportunidade=resultado.score_oportunidade,
            score_saturacao=resultado.score_saturacao,
            acao_recomendada=resultado.acao_recomendada,
            motivo=resultado.motivo,
        )
        for posicao, resultado in oportunidades
    ]
