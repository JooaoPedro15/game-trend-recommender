# Fit real do canal (Sprint 9.1): mede se um jogo realmente funcionou nos MEUS videos,
# a partir de data/meus_videos.csv. Diferente do fit_inicial (um palpite a priori no
# jogos_seed.csv), o fit_real e medido: a media do score_resultado_real dos meus videos
# daquele jogo. Funcao pura (recebe meus_videos ja lidos), nao toca disco nem o ranking.

from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo


# Agrupa os meus videos por jogo detectado (chave em casefold). Videos sem jogo ficam de fora.
def agrupar_meus_videos_por_jogo(meus_videos: list[MeuVideo]) -> dict[str, list[MeuVideo]]:
    grupos: dict[str, list[MeuVideo]] = {}
    for video in meus_videos:
        chave = video.jogo_detectado.strip().casefold()
        if chave:
            grupos.setdefault(chave, []).append(video)
    return grupos


# Fit real de um jogo: a media (0-100) do score_resultado_real dos meus videos desse jogo.
# `jogo` e o nome do jogo (casa com jogo_detectado, ignorando maiusculas). Se o jogo nunca
# apareceu no meu canal, devolve None — "ainda nao testado", sem dado: nao penaliza, so
# sinaliza ausencia, para quem usar decidir o neutro (a futura integracao no ranking).
def calcular_fit_real_jogo(jogo: str, meus_videos: list[MeuVideo]) -> float | None:
    videos = agrupar_meus_videos_por_jogo(meus_videos).get(jogo.strip().casefold(), [])
    if not videos:
        return None

    scores = [calcular_score_resultado_real(video) for video in videos]
    return round(sum(scores) / len(scores), 1)
