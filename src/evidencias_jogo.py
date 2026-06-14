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
