import csv
from pathlib import Path

from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia


# Gera um relatorio em Markdown com os resultados do ranking.
def gerar_relatorio_markdown(caminho: str | Path, ranking) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    linhas = []
    linhas.append("# Ranking de Games Recomendados")
    linhas.append("")

    if not ranking:
        linhas.append("Nenhum jogo foi detectado nos videos coletados.")
    else:
        for posicao, resultado in enumerate(ranking, start=1):
            linhas.append(f"## {posicao}. {resultado.jogo.nome}")
            linhas.append("")
            linhas.append(f"Score final: {resultado.score_final:.1f}")
            linhas.append(f"Tendencia: {resultado.score_tendencia:.1f}")
            linhas.append(f"Fit com o canal: {resultado.score_fit_canal:.1f}")
            linhas.append(f"Descoberta: {resultado.score_descoberta:.1f}")
            linhas.append(f"Saturacao: {resultado.score_saturacao:.1f}")
            linhas.append(f"Videos encontrados: {resultado.videos_encontrados}")
            linhas.append(f"Canais diferentes: {resultado.canais_diferentes}")
            linhas.append("")
            linhas.append(f"Motivo: {resultado.motivo}")
            linhas.append("")
            linhas.append("### Videos que influenciaram")
            linhas.append("")

            for video in resultado.videos:
                taxa_engajamento = calcular_taxa_engajamento(video) * 100
                views_por_dia = calcular_views_por_dia(video)
                linhas.append(
                    f"- {video.canal} | {video.plataforma} | "
                    f"{video.views} views | {video.likes} likes | "
                    f"{video.comentarios} comentarios | "
                    f"{taxa_engajamento:.1f}% engajamento | "
                    f"{views_por_dia:.0f} views/dia | "
                    f"{video.data_publicacao} | {video.titulo}"
                )
                linhas.append(f"  - {video.url}")

            linhas.append("")

    caminho.write_text("\n".join(linhas), encoding="utf-8")


CAMPOS_CSV = [
    "posicao",
    "nome_jogo",
    "score_final",
    "score_tendencia",
    "score_fit_canal",
    "score_descoberta",
    "score_saturacao",
    "videos_encontrados",
    "canais_diferentes",
    "motivo",
]


# Gera um relatorio do ranking em CSV, com uma linha por jogo.
def gerar_relatorio_csv(caminho: str | Path, ranking) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        for posicao, resultado in enumerate(ranking, start=1):
            escritor.writerow(
                {
                    "posicao": posicao,
                    "nome_jogo": resultado.jogo.nome,
                    "score_final": resultado.score_final,
                    "score_tendencia": resultado.score_tendencia,
                    "score_fit_canal": resultado.score_fit_canal,
                    "score_descoberta": resultado.score_descoberta,
                    "score_saturacao": resultado.score_saturacao,
                    "videos_encontrados": resultado.videos_encontrados,
                    "canais_diferentes": resultado.canais_diferentes,
                    "motivo": resultado.motivo,
                }
            )