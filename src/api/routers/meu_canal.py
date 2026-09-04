from fastapi import APIRouter

import config
from api import dependencies
from api.schemas import CandidatoRepeticaoOut, ComparacaoJogoOut, JogoQueFalhouOut, MeuVideoSemJogoOut
from comparacao_meu_canal import comparar_recomendacoes_com_meu_canal
from jogos_falhos import jogos_que_nao_funcionaram
from meus_videos import listar_meus_videos_sem_jogo, sugestao_deteccao
from repetir_jogos import jogos_para_repetir

router = APIRouter(prefix="/meu-canal", tags=["meu-canal"])


@router.get("/sem-jogo", response_model=list[MeuVideoSemJogoOut])
def obter_meu_canal_sem_jogo():
    # Mesmo wrapper de erro (503 em leitura ilegivel) dos outros endpoints, via
    # dependencies._seguro - listar_meus_videos_sem_jogo so aceita um caminho direto.
    videos = dependencies._seguro(
        listar_meus_videos_sem_jogo, config.MEUS_VIDEOS_CSV, "meus_videos.csv"
    )
    return [
        MeuVideoSemJogoOut(
            titulo=video.titulo,
            data_publicacao=video.data_publicacao,
            views=video.views,
            confianca_jogo=video.confianca_jogo,
            fonte_deteccao=video.fonte_deteccao,
            url=video.url,
            sugestao=sugestao_deteccao(video.titulo),
        )
        for video in videos
    ]


@router.get("/comparacao", response_model=list[ComparacaoJogoOut])
def obter_meu_canal_comparacao():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    comparacoes = comparar_recomendacoes_com_meu_canal(ranking, meus_videos)
    return [ComparacaoJogoOut.model_validate(c) for c in comparacoes]


@router.get("/repetir", response_model=list[CandidatoRepeticaoOut])
def obter_meu_canal_repetir():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    candidatos = jogos_para_repetir(ranking, meus_videos)
    return [CandidatoRepeticaoOut.model_validate(c) for c in candidatos]


@router.get("/falhos", response_model=list[JogoQueFalhouOut])
def obter_meu_canal_falhos():
    ranking = dependencies.carregar_ranking()
    meus_videos = dependencies.carregar_meus_videos()
    falhos = jogos_que_nao_funcionaram(ranking, meus_videos)
    return [JogoQueFalhouOut.model_validate(f) for f in falhos]
