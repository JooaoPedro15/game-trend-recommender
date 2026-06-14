from collections import defaultdict
from unicodedata import combining, normalize
from datetime import date
from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia

from detector_jogo import detectar_jogos_no_video
from evidencias_jogo import calcular_score_evidencia_criadores, evidencia_de_video
from modelos import (
    CanalReferencia,
    JogoSeed,
    ResultadoRecomendacao,
    VideoColetado,
)


FRASES_DESCOBERTA = [
    "qual o nome do jogo",
    "que jogo e esse",
    "qual nome",
    "nome?",
    "que jogo",
    "jogo?",
    "qual game",
    "what game",
    "game name",
    "nome do game",
    "nome do jogo",
    "onde baixa",
    "tem na steam",
    "steam?",
    "link do jogo",
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
        videos_ordenados = _ordenar_videos_por_influencia(videos_jogo)
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
        score_oportunidade = _calcular_score_oportunidade(
            score_tendencia, score_saturacao, score_descoberta
        )
        score_evidencia = calcular_score_evidencia_criadores(
            [evidencia_de_video(video) for video in videos_jogo]
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
                    jogo,
                    videos_jogo,
                    score_tendencia,
                    score_descoberta,
                    score_saturacao,
                    score_oportunidade,
                    canais_diferentes,
                ),
                videos=videos_ordenados,
                score_oportunidade=round(score_oportunidade, 1),
                acao_recomendada=_gerar_acao_recomendada(
                    score_oportunidade,
                    score_fit_canal,
                    score_saturacao,
                    score_tendencia,
                    len(videos_jogo),
                ),
                score_evidencia_criadores=round(score_evidencia, 1),
            )
        )

    return sorted(resultados, key=lambda resultado: resultado.score_final, reverse=True)


# Filtra o ranking para apenas as oportunidades prioritarias, preservando a posicao
# original de cada jogo. Criterios heuristicos do MVP (calibrar depois): bom score
# geral, oportunidade alta, pouca saturacao e pelo menos um video coletado.
def filtrar_oportunidades(
    ranking: list[ResultadoRecomendacao],
) -> list[tuple[int, ResultadoRecomendacao]]:
    return [
        (posicao, resultado)
        for posicao, resultado in enumerate(ranking, start=1)
        if resultado.score_oportunidade >= 70
        and resultado.score_final >= 60
        and resultado.score_saturacao >= 55
        and resultado.videos_encontrados >= 1
    ]


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

    for video in videos:
        peso_canal = pesos_canais.get(video.canal.casefold(), 1.0)
        peso_recencia = _calcular_peso_recencia(video.data_publicacao)
        total += _score_video(video) * peso_canal * peso_recencia

    return total


# Pesos iniciais do MVP: views de plataformas de autoplay (TikTok/Reels) valem um
# pouco menos que views do YouTube. Calibrar depois, comparando com resultados reais.
PESOS_PLATAFORMA = {
    "youtube": 1.0,
    "shorts": 0.9,
    "tiktok": 0.8,
    "instagram": 0.8,
}


# Retorna o peso base da plataforma (1.0 para plataformas desconhecidas).
def peso_base_plataforma(plataforma: str) -> float:
    return PESOS_PLATAFORMA.get(plataforma.strip().casefold(), 1.0)


def _score_video(video: VideoColetado) -> float:
    taxa_engajamento = calcular_taxa_engajamento(video)
    bonus_engajamento = video.views * taxa_engajamento * 2
    bonus_velocidade = _calcular_bonus_velocidade(video)

    score_bruto = (
        video.views
        + video.likes * 5
        + video.comentarios * 20
        + bonus_engajamento
        + bonus_velocidade
    )
    return score_bruto * peso_base_plataforma(video.plataforma)


def _calcular_bonus_velocidade(video: VideoColetado) -> float:
    velocidade = max(calcular_views_por_dia(video), 0.0)
    teto = max(video.views, 0) * 0.5

    return min(velocidade * 0.5, teto)


def _calcular_peso_recencia(data_publicacao: str) -> float:
    try:
        data_video = date.fromisoformat(data_publicacao)
    except ValueError:
        return 1.0

    dias = (date.today() - data_video).days

    if dias <= 7:
        return 1.3

    if dias <= 30:
        return 1.1

    if dias <= 90:
        return 0.9

    return 0.6


def _calcular_score_descoberta(videos: list[VideoColetado]) -> float:
    if not videos:
        return 0.0

    videos_com_sinal = 0
    total_sinais = 0

    for video in videos:
        texto = _normalizar_texto(f"{video.titulo} {video.texto_comentarios}")
        sinais_no_video = sum(1 for frase in FRASES_DESCOBERTA if frase in texto)
        if sinais_no_video:
            videos_com_sinal += 1
            total_sinais += sinais_no_video

    proporcao_videos = videos_com_sinal / len(videos)
    bonus_repeticao = min(total_sinais, 3) * 10
    return _limitar(proporcao_videos * 70 + bonus_repeticao)


# Traduz os scores em um proximo passo pratico para o creator. Regras simples,
# em ordem de prioridade: veto por saturacao vem antes de qualquer "priorizar".
def _gerar_acao_recomendada(
    score_oportunidade: float,
    score_fit_canal: float,
    score_saturacao: float,
    score_tendencia: float,
    videos_encontrados: int,
) -> str:
    if score_saturacao <= 40:
        return "Evitar por saturacao alta"

    if score_oportunidade >= 75 and score_fit_canal >= 80:
        return "Priorizar para video longo"

    if score_oportunidade >= 75:
        return "Testar em Short"

    if videos_encontrados <= 1 and score_tendencia < 70:
        return "Pesquisar mais videos antes de gravar"

    return "Monitorar por mais alguns dias"


# Combina performance com espaco para entrar: bom desempenho, pouca saturacao e
# publico ainda perguntando pelo jogo. Velocidade/recencia ja entram via tendencia.
def _calcular_score_oportunidade(
    score_tendencia: float, score_saturacao: float, score_descoberta: float
) -> float:
    return _limitar(
        score_tendencia * 0.40 + score_saturacao * 0.40 + score_descoberta * 0.20
    )


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
    jogo: JogoSeed,
    videos: list[VideoColetado],
    score_tendencia: float,
    score_descoberta: float,
    score_saturacao: float,
    score_oportunidade: float,
    canais_diferentes: int,
) -> str:
    maior_views = max((video.views for video in videos), default=0)
    tem_alta_performance = score_tendencia >= 70 or maior_views >= 500_000
    tem_curiosidade = score_descoberta >= 50
    tem_varios_canais = canais_diferentes > 1
    tem_fit_alto = jogo.fit_inicial >= 8
    tem_poucos_canais = score_saturacao >= 75
    tem_alta_oportunidade = score_oportunidade >= 75
    tem_muitos_canais = score_saturacao <= 55
    tem_video_recente = _tem_video_recente(videos)
    tem_engajamento_alto = _tem_engajamento_alto(videos)

    if tem_alta_oportunidade and tem_poucos_canais and tem_engajamento_alto:
        return (
            "Jogo ainda aparece em poucos canais, mas tem boa velocidade e alto "
            "engajamento, indicando oportunidade antes da saturacao."
        )

    if tem_alta_performance and tem_muitos_canais:
        return (
            "Jogo esta em alta, mas ja aparece em varios canais de referencia; "
            "vale entrar apenas com um angulo diferente."
        )

    if tem_engajamento_alto and tem_video_recente:
     return "Jogo apareceu em video recente com alto engajamento, indicando interesse atual do publico."

    if tem_engajamento_alto and tem_alta_performance:
     return "Jogo teve alto engajamento em videos coletados, indicando forte interesse do publico."

    if tem_video_recente and tem_alta_performance:
     return "Jogo apareceu em videos recentes com boa performance, indicando tendencia atual."

    if tem_alta_performance and tem_curiosidade:
        return "Jogo apareceu em videos com alta performance e comentarios de curiosidade."

    if tem_fit_alto and tem_varios_canais:
        return "Jogo tem alto fit com o canal e apareceu em mais de um canal de referencia."

    if tem_poucos_canais and tem_alta_performance:
        return "Jogo ainda apareceu em poucos canais, mas teve boa performance, indicando possivel oportunidade."

    if tem_fit_alto and tem_curiosidade:
        return "Jogo combina com o canal e gerou curiosidade nos comentarios."

    if tem_fit_alto and len(videos) == 1 and not tem_alta_performance:
        return (
            "Jogo combina com o canal, mas ainda ha pouca evidencia coletada; "
            "vale observar mais alguns videos."
        )

    if tem_fit_alto:
        return "Jogo tem bom fit inicial com o canal e foi detectado nos videos coletados."

    return f"Jogo encontrado em {len(videos)} video(s) coletado(s)."


def _ordenar_videos_por_influencia(videos: list[VideoColetado]) -> list[VideoColetado]:
    return sorted(videos, key=_score_video, reverse=True)


def _normalizar_texto(texto: str) -> str:
    texto_sem_acento = "".join(
        caractere
        for caractere in normalize("NFKD", texto)
        if not combining(caractere)
    )
    return texto_sem_acento.casefold()

def _tem_video_recente(videos: list[VideoColetado]) -> bool:
    for video in videos:
        try:
            data_video = date.fromisoformat(video.data_publicacao)
        except ValueError:
            continue

        dias = (date.today() - data_video).days

        if dias <= 7:
            return True

    return False

# Verifica se algum video teve uma taxa de engajamento alta.
def _tem_engajamento_alto(videos: list[VideoColetado]) -> bool:
    for video in videos:
        taxa_engajamento = calcular_taxa_engajamento(video)

        if video.views >= 10000 and taxa_engajamento >= 0.10:
            return True

    return False
