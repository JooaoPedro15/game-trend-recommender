import csv
from pathlib import Path

from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia
from evidencias_jogo import gerar_evidencias, resumir_evidencia_criadores


# Formata o fit real para os relatorios: "n/d" quando o jogo nunca apareceu no meu canal.
def _formatar_fit_real(score_fit_real: float | None) -> str:
    return "n/d" if score_fit_real is None else f"{score_fit_real:.1f}"


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
            linhas.append(f"Fit real (meu canal): {_formatar_fit_real(resultado.score_fit_real)}")
            linhas.append(f"Formato sugerido: {resultado.formato_sugerido or 'n/d'}")
            linhas.append(f"Descoberta: {resultado.score_descoberta:.1f}")
            linhas.append(f"Saturacao: {resultado.score_saturacao:.1f}")
            linhas.append(f"Oportunidade: {resultado.score_oportunidade:.1f}")
            linhas.append(f"Evidencia criadores: {resultado.score_evidencia_criadores:.1f}")
            linhas.append(f"Evidencia no meu nicho: {resultado.score_evidencia_nicho:.1f}")
            linhas.append(f"Videos encontrados: {resultado.videos_encontrados}")
            linhas.append(f"Canais diferentes: {resultado.canais_diferentes}")
            linhas.append("")
            linhas.append(f"Motivo: {resultado.motivo}")
            linhas.append(f"Acao recomendada: {resultado.acao_recomendada}")
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
    "score_fit_real",
    "formato_sugerido",
    "score_descoberta",
    "score_saturacao",
    "score_oportunidade",
    "score_evidencia_criadores",
    "score_evidencia_nicho",
    "videos_encontrados",
    "canais_diferentes",
    "motivo",
    "acao_recomendada",
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
                    "score_fit_real": (
                        "" if resultado.score_fit_real is None else resultado.score_fit_real
                    ),
                    "formato_sugerido": resultado.formato_sugerido,
                    "score_descoberta": resultado.score_descoberta,
                    "score_saturacao": resultado.score_saturacao,
                    "score_oportunidade": resultado.score_oportunidade,
                    "score_evidencia_criadores": resultado.score_evidencia_criadores,
                    "score_evidencia_nicho": resultado.score_evidencia_nicho,
                    "videos_encontrados": resultado.videos_encontrados,
                    "canais_diferentes": resultado.canais_diferentes,
                    "motivo": resultado.motivo,
                    "acao_recomendada": resultado.acao_recomendada,
                }
            )


# Gera um relatorio em Markdown com os jogos ranqueados e os videos/criadores que
# servem de evidencia para cada um, ordenado pelo score de evidencia de criadores.
def gerar_relatorio_evidencias_markdown(
    caminho: str | Path, ranking, canais=None
) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    evidencias_por_jogo = gerar_evidencias(ranking, canais)
    jogos_ordenados = sorted(
        ranking, key=lambda r: r.score_evidencia_criadores, reverse=True
    )

    linhas = []
    linhas.append("# Evidencias por Jogo")
    linhas.append("")

    if not jogos_ordenados:
        linhas.append("Nenhum jogo foi detectado nos videos coletados.")
    else:
        for posicao, resultado in enumerate(jogos_ordenados, start=1):
            evidencias = evidencias_por_jogo.get(resultado.jogo.nome, [])
            linhas.append(f"## {posicao}. {resultado.jogo.nome}")
            linhas.append("")
            linhas.append(
                f"Score de evidencia: {resultado.score_evidencia_criadores:.1f}"
            )
            linhas.append(f"Resumo: {resumir_evidencia_criadores(evidencias)}")
            linhas.append("")
            linhas.append("### Videos que servem de evidencia")
            linhas.append("")

            for ordem, evidencia in enumerate(evidencias, start=1):
                linhas.append(
                    f"{ordem}. {evidencia.canal} | {evidencia.nicho} | "
                    f"{evidencia.tipo_conteudo} | {evidencia.plataforma} | "
                    f"{evidencia.tipo_video} | {evidencia.views} views | "
                    f"{evidencia.taxa_engajamento:.1f}% engajamento | "
                    f"{evidencia.views_por_dia:.0f} views/dia | "
                    f"similaridade {evidencia.peso_similaridade:.1f} | "
                    f"viralidade {evidencia.score_viralidade_video:.1f}"
                )
                linhas.append(f"   - Titulo: {evidencia.titulo}")
                linhas.append(f"   - Link: {evidencia.url}")

            linhas.append("")

    caminho.write_text("\n".join(linhas), encoding="utf-8")