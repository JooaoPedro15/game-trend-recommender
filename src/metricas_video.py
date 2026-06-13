from datetime import date

from modelos import VideoColetado


# Calcula a taxa de engajamento de um video.
def calcular_taxa_engajamento(video: VideoColetado) -> float:
    if video.views <= 0:
        return 0.0

    return (video.likes + video.comentarios) / video.views


def calcular_views_por_dia(video: VideoColetado) -> float:
    try:
        data_video = date.fromisoformat(video.data_publicacao)
    except ValueError:
        return 0.0

    idade_em_dias = max((date.today() - data_video).days, 1)
    return video.views / idade_em_dias


def views_por_dia(video: VideoColetado) -> float:
    return calcular_views_por_dia(video)


# Referencias do que conta como "viral" (heuristicas do MVP, calibrar depois).
VIEWS_VIRAL = 1_000_000
ENGAJAMENTO_VIRAL = 0.10        # 10% de likes+comentarios por view
VELOCIDADE_VIRAL = 100_000      # views por dia


# Pontua de 0 a 100 quanto um video performou (viralizou), somando 4 componentes
# limitados: volume (40), engajamento (30), velocidade (20) e recencia (10). Reusa
# calcular_taxa_engajamento e calcular_views_por_dia. peso_canal (>= 0) e um
# multiplicador opcional do canal de referencia (1.0 = neutro); o total fica em 0-100.
def calcular_score_viralidade_video(video: VideoColetado, peso_canal: float = 1.0) -> float:
    pontos_volume = min(video.views / VIEWS_VIRAL, 1.0) * 40
    pontos_engajamento = min(calcular_taxa_engajamento(video) / ENGAJAMENTO_VIRAL, 1.0) * 30
    pontos_velocidade = min(calcular_views_por_dia(video) / VELOCIDADE_VIRAL, 1.0) * 20
    pontos_recencia = _pontos_recencia(video.data_publicacao)

    base = pontos_volume + pontos_engajamento + pontos_velocidade + pontos_recencia
    return round(min(base * peso_canal, 100.0), 1)


# Bonus de recencia (0 a 10): videos mais novos pontuam mais.
def _pontos_recencia(data_publicacao: str) -> float:
    try:
        data_video = date.fromisoformat(data_publicacao)
    except ValueError:
        return 0.0

    dias = (date.today() - data_video).days
    if dias <= 7:
        return 10.0
    if dias <= 30:
        return 6.0
    if dias <= 90:
        return 3.0
    return 0.0
