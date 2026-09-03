# Funcoes de carregamento por requisicao: leem os CSVs configurados em config.py e
# devolvem os dados ja no formato dos dataclasses internos, ou levantam 503 se o
# arquivo existir mas nao puder ser lido. Arquivo AUSENTE nao e erro: os leitores de
# CSV ja devolvem lista vazia nesse caso (mesmo comportamento da CLI).

import csv

from fastapi import HTTPException

import config
import ranking_service
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from meus_videos import ler_meus_videos
from watchlist import listar_jogos as _listar_jogos_watchlist


def _seguro(func, caminho, descricao: str):
    try:
        return func(caminho)
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel ler {descricao}: {erro}")


def carregar_jogos():
    return _seguro(ler_jogos_seed, config.DATA_DIR / "jogos_seed.csv", "jogos_seed.csv")


def carregar_canais():
    return _seguro(
        ler_canais_referencia, config.DATA_DIR / "canais_referencia.csv", "canais_referencia.csv"
    )


def carregar_videos():
    return _seguro(ler_videos_coletados, config.VIDEOS_CSV, "videos_coletados.csv")


def carregar_meus_videos():
    return _seguro(ler_meus_videos, config.MEUS_VIDEOS_CSV, "meus_videos.csv")


def carregar_watchlist():
    return _seguro(_listar_jogos_watchlist, config.WATCHLIST_CSV, "watchlist_jogos.csv")


def carregar_ranking(plataforma: str | None = None, top: int | None = None, desde=None):
    try:
        return ranking_service.carregar_ranking(
            config.DATA_DIR, config.VIDEOS_CSV, config.MEUS_VIDEOS_CSV, plataforma, top, desde
        )
    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise HTTPException(status_code=503, detail=f"Nao foi possivel montar o ranking: {erro}")
