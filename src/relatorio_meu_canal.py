# Relatorio de aprendizado do meu canal (Sprint 8.10): consolida data/meus_videos.csv
# em um panorama de o que funcionou comigo — melhores videos, jogos e formatos. Tudo
# por agregacao aritmetica + ordenacao (sem IA). Apenas descreve e sugere acoes
# operacionais; nunca cria roteiro, gancho ou tom de voz. Nao mexe no ranking.

from dataclasses import dataclass
from pathlib import Path

from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo


# Um video meu com o seu resultado real ja calculado (para ordenar/listar).
@dataclass
class VideoComScore:
    video: MeuVideo
    score: float


# Desempenho agregado de um jogo nos meus videos.
@dataclass
class DesempenhoJogo:
    jogo: str
    videos: int
    melhor_score: float
    media_score: float


# Desempenho agregado de um formato (curto/longo/live/desconhecido) nos meus videos.
@dataclass
class DesempenhoFormato:
    tipo_video: str
    videos: int
    media_score: float


# Os meus videos ordenados pelo resultado real (desc), ate o limite. Cada item carrega
# o video e o score, para a lista e o relatorio nao recalcularem o score duas vezes.
def melhores_videos(meus_videos: list[MeuVideo], limite: int = 10) -> list[VideoComScore]:
    com_score = [
        VideoComScore(video, calcular_score_resultado_real(video)) for video in meus_videos
    ]
    com_score.sort(key=lambda item: item.score, reverse=True)
    return com_score[:limite]


# Agrupa os videos por jogo detectado (ignora os sem jogo) e resume cada grupo:
# quantidade, melhor resultado e media. Ordena pelo melhor resultado (depois pela media).
def desempenho_por_jogo(meus_videos: list[MeuVideo]) -> list[DesempenhoJogo]:
    grupos: dict[str, list[float]] = {}
    for video in meus_videos:
        jogo = video.jogo_detectado.strip()
        if jogo:
            grupos.setdefault(jogo, []).append(calcular_score_resultado_real(video))

    desempenhos = [
        DesempenhoJogo(jogo, len(scores), max(scores), round(sum(scores) / len(scores), 1))
        for jogo, scores in grupos.items()
    ]
    desempenhos.sort(key=lambda d: (d.melhor_score, d.media_score), reverse=True)
    return desempenhos


# Agrupa todos os videos por formato (tipo_video) e resume a media de resultado de cada um.
# Inclui ate os sem jogo: o formato performa independente de o jogo ter sido detectado.
def desempenho_por_formato(meus_videos: list[MeuVideo]) -> list[DesempenhoFormato]:
    grupos: dict[str, list[float]] = {}
    for video in meus_videos:
        tipo = video.tipo_video or "desconhecido"
        grupos.setdefault(tipo, []).append(calcular_score_resultado_real(video))

    desempenhos = [
        DesempenhoFormato(tipo, len(scores), round(sum(scores) / len(scores), 1))
        for tipo, scores in grupos.items()
    ]
    desempenhos.sort(key=lambda d: d.media_score, reverse=True)
    return desempenhos


# Recomendacoes operacionais simples (logisticas, nunca criativas): qual formato priorizar,
# qual jogo revisitar e quantos videos precisam de correcao de deteccao.
def _recomendacoes(
    meus_videos: list[MeuVideo],
    por_jogo: list[DesempenhoJogo],
    por_formato: list[DesempenhoFormato],
) -> list[str]:
    recomendacoes = []
    if por_formato:
        melhor = por_formato[0]
        recomendacoes.append(
            f'Formato de melhor media: "{melhor.tipo_video}" '
            f"(media {melhor.media_score:.1f}) - priorize esse formato."
        )
    if por_jogo:
        topo = por_jogo[0]
        recomendacoes.append(
            f'Jogo que mais funcionou: "{topo.jogo}" '
            f"(melhor resultado {topo.melhor_score:.1f}) - vale revisitar."
        )
    sem_jogo = sum(1 for video in meus_videos if not video.jogo_detectado.strip())
    if sem_jogo:
        recomendacoes.append(
            f"{sem_jogo} video(s) sem jogo detectado - rode \"meus_videos_sem_jogo\" e "
            "corrija alias/descricao para nao perder esse aprendizado."
        )
    if not recomendacoes:
        recomendacoes.append('Sem dados suficientes ainda — colete videos com "coletar_meu_canal".')
    return recomendacoes


# Gera o relatorio de aprendizado em Markdown a partir dos meus videos (lista de MeuVideo).
# Funcao de formatacao: a leitura do CSV e o timestamp do arquivo ficam no main.
def gerar_relatorio_meu_canal_markdown(
    caminho: str | Path, meus_videos: list[MeuVideo], limite_videos: int = 10
) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    linhas = ["# Relatorio de Aprendizado do Meu Canal", ""]

    if not meus_videos:
        linhas.append('Nenhum video coletado ainda. Rode "coletar_meu_canal" primeiro.')
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        return

    por_jogo = desempenho_por_jogo(meus_videos)
    por_formato = desempenho_por_formato(meus_videos)
    melhores = melhores_videos(meus_videos, limite_videos)
    sem_jogo = sorted(
        (video for video in meus_videos if not video.jogo_detectado.strip()),
        key=lambda video: video.views,
        reverse=True,
    )

    linhas.append(f"Total de videos analisados: {len(meus_videos)}")
    linhas.append("")

    linhas.append("## Melhores videos por resultado real")
    linhas.append("")
    for item in melhores:
        video = item.video
        linhas.append(
            f"- {item.score:.1f} | {video.jogo_detectado or '(sem jogo)'} | "
            f"{video.tipo_video} | {video.views} views | "
            f"{video.data_publicacao} | {video.titulo}"
        )
        linhas.append(f"  - {video.url}")
    linhas.append("")

    linhas.append("## Jogos que mais funcionaram")
    linhas.append("")
    if not por_jogo:
        linhas.append("Nenhum jogo detectado nos seus videos ainda.")
    else:
        for desempenho in por_jogo:
            linhas.append(
                f"- {desempenho.jogo} | melhor {desempenho.melhor_score:.1f} | "
                f"media {desempenho.media_score:.1f} | {desempenho.videos} video(s)"
            )
    linhas.append("")

    linhas.append("## Formatos que performaram melhor")
    linhas.append("")
    for desempenho in por_formato:
        linhas.append(
            f"- {desempenho.tipo_video} | media {desempenho.media_score:.1f} | "
            f"{desempenho.videos} video(s)"
        )
    linhas.append("")

    linhas.append("## Videos sem jogo detectado")
    linhas.append("")
    if not sem_jogo:
        linhas.append("Todos os seus videos tem um jogo detectado.")
    else:
        for video in sem_jogo:
            linhas.append(f"- {video.views} views | {video.data_publicacao} | {video.titulo}")
            linhas.append(f"  - {video.url}")
    linhas.append("")

    linhas.append("## Recomendacoes operacionais")
    linhas.append("")
    for recomendacao in _recomendacoes(meus_videos, por_jogo, por_formato):
        linhas.append(f"- {recomendacao}")
    linhas.append("")

    caminho.write_text("\n".join(linhas), encoding="utf-8")
