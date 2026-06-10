from datetime import date

from modelos import VideoColetado


# Calcula a taxa de engajamento de um video.
def calcular_taxa_engajamento(video: VideoColetado) -> float:
    if video.views <= 0:
        return 0.0

    return (video.likes + video.comentarios) / video.views


def views_por_dia(video: VideoColetado) -> float:
    try:
        data_video = date.fromisoformat(video.data_publicacao)
    except ValueError:
        return 0.0

    idade_em_dias = max((date.today() - data_video).days, 1)
    return video.views / idade_em_dias
