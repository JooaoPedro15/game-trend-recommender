from pathlib import Path


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
                linhas.append(
                    f"- {video.canal} | {video.plataforma} | "
                    f"{video.views} views | {video.likes} likes | "
                    f"{video.comentarios} comentarios | "
                    f"{video.data_publicacao} | {video.titulo}"
                )
                linhas.append(f"  - {video.url}")

            linhas.append("")

    caminho.write_text("\n".join(linhas), encoding="utf-8")