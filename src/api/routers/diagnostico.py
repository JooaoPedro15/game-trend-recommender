from fastapi import APIRouter

from api import dependencies
from api.schemas import DescobertaOut, DiagnosticoOut, VideoSemJogoOut
from descobertas import descobertas_sem_jogo
from diagnostico_dados import encontrar_videos_sem_jogo, gerar_diagnostico

router = APIRouter(tags=["diagnostico"])


@router.get("/diagnostico", response_model=DiagnosticoOut)
def obter_diagnostico():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return DiagnosticoOut.model_validate(gerar_diagnostico(videos, jogos))


@router.get("/videos-sem-jogo", response_model=list[VideoSemJogoOut])
def obter_videos_sem_jogo():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return [VideoSemJogoOut.model_validate(v) for v in encontrar_videos_sem_jogo(videos, jogos)]


@router.get("/descobertas-sem-jogo", response_model=list[DescobertaOut])
def obter_descobertas_sem_jogo():
    videos = dependencies.carregar_videos()
    jogos = dependencies.carregar_jogos()
    return [DescobertaOut.model_validate(d) for d in descobertas_sem_jogo(videos, jogos)]
