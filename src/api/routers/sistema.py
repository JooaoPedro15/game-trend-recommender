import csv

from fastapi import APIRouter, HTTPException

import config
from api.schemas import ComparacaoRankingsOut, StatusOut
from config import obter_meu_canal_youtube_id, obter_youtube_api_key
from historico_ranking import comparar_ultimas_execucoes
from status_sistema import coletar_status

router = APIRouter(tags=["sistema"])


@router.get("/status", response_model=StatusOut)
def obter_status():
    try:
        status = coletar_status(
            chave_configurada=obter_youtube_api_key() is not None,
            canal_configurado=obter_meu_canal_youtube_id() is not None,
            caminho_videos=config.VIDEOS_CSV,
            caminho_meus_videos=config.MEUS_VIDEOS_CSV,
            caminho_jogos=config.DATA_DIR / "jogos_seed.csv",
            caminho_canais=config.DATA_DIR / "canais_referencia.csv",
            caminho_historico=config.HISTORICO_CSV,
            dir_relatorios=config.REPORTS_DIR,
        )
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel montar o status: {erro}")
    return StatusOut.model_validate(status)


@router.get("/historico/comparacao", response_model=ComparacaoRankingsOut)
def obter_historico_comparacao():
    try:
        comparacao = comparar_ultimas_execucoes(config.HISTORICO_CSV)
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel ler o historico: {erro}")
    if comparacao is None:
        raise HTTPException(
            status_code=409,
            detail="Historico insuficiente: sao necessarias pelo menos duas execucoes salvas.",
        )
    return ComparacaoRankingsOut.model_validate(comparacao)
