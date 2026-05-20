from modelos import VideoColetado


# Calcula a taxa de engajamento de um video.
def calcular_taxa_engajamento(video: VideoColetado) -> float:
    if video.views <= 0:
        return 0.0

    return (video.likes + video.comentarios) / video.views