# Fit real do canal (Sprint 9.1): mede se um jogo realmente funcionou nos MEUS videos,
# a partir de data/meus_videos.csv. Diferente do fit_inicial (um palpite a priori no
# jogos_seed.csv), o fit_real e medido: a media do score_resultado_real dos meus videos
# daquele jogo. Funcao pura (recebe meus_videos ja lidos), nao toca disco nem o ranking.

from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo, ResultadoRecomendacao


# Formatos que faz sentido sugerir como operacao (desconhecido nunca e sugerido).
FORMATOS_SUGERIVEIS = ("curto", "longo", "live")

# Um formato so e sugerido pelo historico se a media dele for boa (heuristica do MVP).
LIMIAR_FORMATO_BOM = 50.0


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


# Performance media (score_resultado_real) por tipo_video nos meus videos de um jogo.
# Devolve {tipo_video: media}; vazio se o jogo nunca apareceu no meu canal.
def desempenho_por_formato_do_jogo(jogo: str, meus_videos: list[MeuVideo]) -> dict[str, float]:
    videos = agrupar_meus_videos_por_jogo(meus_videos).get(jogo.strip().casefold(), [])

    grupos: dict[str, list[float]] = {}
    for video in videos:
        tipo = video.tipo_video or "desconhecido"
        grupos.setdefault(tipo, []).append(calcular_score_resultado_real(video))

    return {tipo: round(sum(scores) / len(scores), 1) for tipo, scores in grupos.items()}


# Sugere o formato operacional (curto/longo/live) com base no que ja funcionou para ESTE
# jogo no meu canal: se algum formato sugerivel teve media boa, devolve o de melhor media.
# Sem historico (ou historico fraco), mantem o formato ja implicito na acao recomendada.
# Devolve "" quando nem o historico nem a acao apontam um formato. Apenas formato — nunca
# roteiro, gancho ou angulo.
def sugerir_formato_por_historico(
    resultado: ResultadoRecomendacao, meus_videos: list[MeuVideo]
) -> str:
    desempenho = desempenho_por_formato_do_jogo(resultado.jogo.nome, meus_videos)
    candidatos = {
        tipo: media for tipo, media in desempenho.items() if tipo in FORMATOS_SUGERIVEIS
    }
    if candidatos:
        melhor_tipo, melhor_media = max(candidatos.items(), key=lambda item: item[1])
        if melhor_media >= LIMIAR_FORMATO_BOM:
            return melhor_tipo

    return _formato_da_acao(resultado.acao_recomendada)


# Extrai o formato ja implicito na acao recomendada do ranking (o "atual"): "longo" ou
# "curto"; "" quando a acao nao aponta um formato especifico.
def _formato_da_acao(acao_recomendada: str) -> str:
    acao = acao_recomendada.casefold()
    if "longo" in acao:
        return "longo"
    if "short" in acao:
        return "curto"
    return ""
