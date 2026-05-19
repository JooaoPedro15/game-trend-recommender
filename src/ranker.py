from collections import defaultdict

from detector_jogo import detectar_jogos_no_video
from modelos import (
    CanalReferencia,
    JogoSeed,
    ResultadoRecomendacao,
    VideoColetado,
)


FRASES_DESCOBERTA = [
    "qual o nome do jogo",
    "que jogo e esse",
    "que jogo é esse",
    "nome do jogo",
    "onde baixa",
    "tem na steam",
    "game name",
]


def calcular_ranking(
    jogos: list[JogoSeed],
    videos: list[VideoColetado],
    canais: list[CanalReferencia],
) -> list[ResultadoRecomendacao]:
    agregados = _agrupar_videos_por_jogo(jogos, videos)
    if not agregados:
        return []

    pesos_canais = {canal.nome.casefold(): canal.peso for canal in canais}
    tendencias_brutas = {
        nome_jogo: _calcular_tendencia_bruta(videos_jogo, pesos_canais)
        for nome_jogo, videos_jogo in agregados.items()
    }
    maior_tendencia = max(tendencias_brutas.values()) or 1.0
    jogos_por_nome = {jogo.nome: jogo for jogo in jogos}

    resultados = []
    for nome_jogo, videos_jogo in agregados.items():
        jogo = jogos_por_nome[nome_jogo]
        canais_diferentes = len({video.canal for video in videos_jogo})
        score_tendencia = _normalizar(tendencias_brutas[nome_jogo], maior_tendencia)
        score_fit_canal = _limitar(jogo.fit_inicial * 10)
        score_descoberta = _calcular_score_descoberta(videos_jogo)
        score_saturacao = _calcular_score_saturacao(canais_diferentes)
        score_final = (
            score_tendencia * 0.40
            + score_fit_canal * 0.35
            + score_descoberta * 0.15
            + score_saturacao * 0.10
        )

        resultados.append(
            ResultadoRecomendacao(
                jogo=jogo,
                score_final=round(score_final, 1),
                score_tendencia=round(score_tendencia, 1),
                score_fit_canal=round(score_fit_canal, 1),
                score_descoberta=round(score_descoberta, 1),
                score_saturacao=round(score_saturacao, 1),
                videos_encontrados=len(videos_jogo),
                canais_diferentes=canais_diferentes,
                motivo=_gerar_motivo(
                    videos_jogo, score_tendencia, score_descoberta, score_saturacao
                ),
            )
        )

    return sorted(resultados, key=lambda resultado: resultado.score_final, reverse=True)


def _agrupar_videos_por_jogo(
    jogos: list[JogoSeed], videos: list[VideoColetado]
) -> dict[str, list[VideoColetado]]:
    agregados = defaultdict(list)

    for video in videos:
        for jogo in detectar_jogos_no_video(video, jogos):
            agregados[jogo.nome].append(video)

    return dict(agregados)


def _calcular_tendencia_bruta(
    videos: list[VideoColetado], pesos_canais: dict[str, float]
) -> float:
    total = 0.0
    canais_diferentes = set()

    for video in videos:
        peso_canal = pesos_canais.get(video.canal.casefold(), 1.0)
        total += _score_video(video) * peso_canal
        canais_diferentes.add(video.canal)

    return total + len(canais_diferentes) * 100_000


def _score_video(video: VideoColetado) -> float:
    return video.views + video.likes * 5 + video.comentarios * 20


def _calcular_score_descoberta(videos: list[VideoColetado]) -> float:
    if not videos:
        return 0.0

    videos_com_sinal = 0
    total_sinais = 0

    for video in videos:
        texto = f"{video.titulo} {video.texto_comentarios}".casefold()
        sinais_no_video = sum(1 for frase in FRASES_DESCOBERTA if frase in texto)
        if sinais_no_video:
            videos_com_sinal += 1
            total_sinais += sinais_no_video

    proporcao_videos = videos_com_sinal / len(videos)
    bonus_repeticao = min(total_sinais, 3) * 10
    return _limitar(proporcao_videos * 70 + bonus_repeticao)


def _calcular_score_saturacao(canais_diferentes: int) -> float:
    # MVP: poucos canais com performance boa indicam oportunidade antes da saturacao.
    if canais_diferentes <= 1:
        return 90.0
    if canais_diferentes == 2:
        return 75.0
    if canais_diferentes == 3:
        return 55.0
    return max(20.0, 55.0 - (canais_diferentes - 3) * 10)


def _normalizar(valor: float, maior_valor: float) -> float:
    if maior_valor <= 0:
        return 0.0
    return _limitar((valor / maior_valor) * 100)


def _limitar(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return max(minimo, min(maximo, valor))


def _gerar_motivo(
    videos: list[VideoColetado],
    score_tendencia: float,
    score_descoberta: float,
    score_saturacao: float,
) -> str:
    partes = []

    if score_tendencia >= 70:
        partes.append("apareceu em videos recentes com boa performance")
    else:
        partes.append("foi mencionado nos videos coletados")

    if score_descoberta >= 50:
        partes.append("comentarios perguntando o nome do jogo")

    if score_saturacao >= 75:
        partes.append("ainda apareceu em poucos canais de referencia")

    if not partes:
        return f"Jogo encontrado em {len(videos)} video(s) coletado(s)."

    return "Jogo " + " e ".join(partes) + "."
