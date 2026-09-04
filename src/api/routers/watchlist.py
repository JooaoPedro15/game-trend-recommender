from datetime import date

from fastapi import APIRouter, Query

from api import dependencies
from api.schemas import WatchlistRankingItemOut
from main import cruzar_watchlist_com_ranking

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=list[str])
def obter_watchlist():
    return dependencies.carregar_watchlist()


@router.get("/watchlist/ranking", response_model=list[WatchlistRankingItemOut])
def obter_watchlist_ranking(
    plataforma: str | None = Query(None),
    top: int | None = Query(None, ge=0),
    desde: date | None = Query(None),
):
    nomes = dependencies.carregar_watchlist()
    ranking = dependencies.carregar_ranking(plataforma, top, desde)

    itens = []
    for nome, posicao, resultado in cruzar_watchlist_com_ranking(nomes, ranking):
        itens.append(
            WatchlistRankingItemOut(
                nome=nome,
                posicao=posicao,
                score_final=resultado.score_final if resultado else None,
                score_oportunidade=resultado.score_oportunidade if resultado else None,
                acao_recomendada=resultado.acao_recomendada if resultado else None,
                motivo=resultado.motivo if resultado else None,
            )
        )
    return itens
