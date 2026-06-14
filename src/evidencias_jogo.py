from dataclasses import dataclass

from metricas_video import (
    calcular_score_viralidade_video,
    calcular_taxa_engajamento,
    calcular_views_por_dia,
)


@dataclass
class EvidenciaVideo:
    canal: str
    plataforma: str
    tipo_video: str
    titulo: str
    url: str
    views: int
    likes: int
    comentarios: int
    taxa_engajamento: float       # em porcentagem (ex: 11.4)
    views_por_dia: float
    score_viralidade_video: float
    data_publicacao: str


# Monta a evidencia de um video, reusando as metricas centralizadas.
def evidencia_de_video(video) -> EvidenciaVideo:
    return EvidenciaVideo(
        canal=video.canal,
        plataforma=video.plataforma,
        tipo_video=video.tipo_video,
        titulo=video.titulo,
        url=video.url,
        views=video.views,
        likes=video.likes,
        comentarios=video.comentarios,
        taxa_engajamento=round(calcular_taxa_engajamento(video) * 100, 1),
        views_por_dia=round(calcular_views_por_dia(video), 1),
        score_viralidade_video=calcular_score_viralidade_video(video),
        data_publicacao=video.data_publicacao,
    )


# Para cada jogo do ranking, monta a lista de evidencias dos videos detectados,
# ordenada por score_viralidade_video (maior primeiro). Devolve nome_jogo -> lista,
# preservando a ordem do ranking.
def gerar_evidencias(ranking) -> dict[str, list[EvidenciaVideo]]:
    evidencias = {}
    for resultado in ranking:
        videos = [evidencia_de_video(video) for video in resultado.videos]
        videos.sort(key=lambda evidencia: evidencia.score_viralidade_video, reverse=True)
        evidencias[resultado.jogo.nome] = videos
    return evidencias


# Mostra as evidencias por jogo no terminal, com os dados uteis e o link.
def imprimir_evidencias(evidencias: dict[str, list[EvidenciaVideo]]) -> None:
    print("=== Evidencias por Jogo ===")
    for nome_jogo, videos in evidencias.items():
        print()
        print(f"{nome_jogo} ({len(videos)} video(s)):")
        if not videos:
            print("  (sem videos detectados)")
            continue
        for evidencia in videos:
            print(
                f"  [viral {evidencia.score_viralidade_video:.0f}] "
                f"{evidencia.canal} | {evidencia.plataforma} | {evidencia.tipo_video} | "
                f"{evidencia.views} views | {evidencia.taxa_engajamento:.1f}% eng | "
                f"{evidencia.views_por_dia:.0f} views/dia | {evidencia.data_publicacao}"
            )
            print(f"    {evidencia.titulo}")
            print(f"    {evidencia.url}")


# Limiares e pesos do score de evidencia (heuristicas do MVP, calibrar depois).
LIMIAR_VIDEO_BOM = 60.0
BONUS_POR_CANAL_EXTRA = 6.0
TETO_BONUS_CANAIS = 18.0
BONUS_POR_VIRAL_EXTRA = 5.0
TETO_BONUS_VIRAIS = 15.0
BONUS_FORMATO = 6.0


# Pontua de 0 a 100 a forca da evidencia de um jogo: media de viralidade dos videos,
# mais bonus por canais diferentes, por varios videos com alta performance e por ter
# curto E longo performando bem. Recebe a lista de EvidenciaVideo do jogo.
def calcular_score_evidencia_criadores(evidencias: list[EvidenciaVideo]) -> float:
    if not evidencias:
        return 0.0

    media = sum(e.score_viralidade_video for e in evidencias) / len(evidencias)
    n_canais = len({e.canal.strip().casefold() for e in evidencias})
    bons = [e for e in evidencias if e.score_viralidade_video >= LIMIAR_VIDEO_BOM]

    bonus_canais = min((n_canais - 1) * BONUS_POR_CANAL_EXTRA, TETO_BONUS_CANAIS)
    bonus_virais = min(max(len(bons) - 1, 0) * BONUS_POR_VIRAL_EXTRA, TETO_BONUS_VIRAIS)
    bonus_curto = BONUS_FORMATO if any(e.tipo_video == "curto" for e in bons) else 0.0
    bonus_longo = BONUS_FORMATO if any(e.tipo_video == "longo" for e in bons) else 0.0

    score = media + bonus_canais + bonus_virais + bonus_curto + bonus_longo
    return round(min(max(score, 0.0), 100.0), 1)


# Texto curto explicando a evidencia (nao gera roteiro, gancho ou tom de voz).
def resumir_evidencia_criadores(evidencias: list[EvidenciaVideo]) -> str:
    if not evidencias:
        return "Nenhum video coletado para este jogo."

    n_canais = len({e.canal.strip().casefold() for e in evidencias})
    bons = [e for e in evidencias if e.score_viralidade_video >= LIMIAR_VIDEO_BOM]
    curtos_bons = sum(1 for e in bons if e.tipo_video == "curto")
    longos_bons = sum(1 for e in bons if e.tipo_video == "longo")

    partes = [f"{n_canais} criador(es) diferente(s) fizeram videos"]
    if bons:
        partes.append(f"{len(bons)} video(s) com alta performance")
    if curtos_bons:
        partes.append(f"{curtos_bons} curto(s) performando bem")
    if longos_bons:
        partes.append(f"{longos_bons} longo(s) performando bem")
    return "; ".join(partes) + "."
