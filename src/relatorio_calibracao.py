# Relatorio de calibracao do ranking (Sprint 9.7): mostra, com os meus proprios videos,
# como os dados do canal estao influenciando as recomendacoes — onde o sistema acertou,
# prometeu e falhou, ou surpreendeu. So compoe blocos que ja existem (comparacao 8.9,
# repeticao 9.5, formatos 8.10, fit real 9.2): aritmetica e formatacao, sem IA. Apenas
# diagnostico; nunca cria roteiro, gancho ou tom de voz.

from pathlib import Path

from comparacao_meu_canal import comparar_recomendacoes_com_meu_canal
from relatorio_meu_canal import desempenho_por_formato
from repetir_jogos import jogos_para_repetir
from modelos import MeuVideo, ResultadoRecomendacao


# Quantos jogos do topo do ranking mostrar na secao de fit real.
LIMITE_PRINCIPAIS = 10


# Gera o relatorio de calibracao em Markdown a partir do ranking atual e dos meus videos.
# Funcao de formatacao: a leitura dos dados e o timestamp do arquivo ficam no main.
def gerar_relatorio_calibracao_markdown(
    caminho: str | Path,
    ranking: list[ResultadoRecomendacao],
    meus_videos: list[MeuVideo],
) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    comparacoes = comparar_recomendacoes_com_meu_canal(ranking, meus_videos)
    por_conclusao = _agrupar_por_conclusao(comparacoes)

    linhas = ["# Relatorio de Calibracao do Ranking", ""]
    linhas.append(
        "Como os dados do meu canal (data/meus_videos.csv) estao influenciando as "
        "recomendacoes do ranking."
    )
    linhas.append("")
    linhas.append(f"Videos do meu canal analisados: {len(meus_videos)}")
    linhas.append(f"Jogos no ranking: {len(ranking)}")
    linhas.append("")

    _secao_comparacao(
        linhas, "Jogos que o sistema acertou", por_conclusao.get("recomendacao_confirmada", [])
    )
    _secao_comparacao(
        linhas,
        "Jogos que prometiam mas nao funcionaram",
        por_conclusao.get("prometia_mas_nao_funcionou", []),
    )
    _secao_comparacao(
        linhas,
        "Jogos que funcionaram melhor que o esperado",
        por_conclusao.get("funcionou_melhor_que_o_esperado", []),
    )
    _secao_comparacao(
        linhas, "Jogos para monitorar", por_conclusao.get("precisa_de_mais_testes", [])
    )
    _secao_repetir(linhas, jogos_para_repetir(ranking, meus_videos))
    _secao_formatos(linhas, desempenho_por_formato(meus_videos))
    _secao_fit_real(linhas, ranking)

    caminho.write_text("\n".join(linhas), encoding="utf-8")


# Agrupa as comparacoes pelo veredicto (conclusao).
def _agrupar_por_conclusao(comparacoes) -> dict[str, list]:
    grupos: dict[str, list] = {}
    for comparacao in comparacoes:
        grupos.setdefault(comparacao.conclusao, []).append(comparacao)
    return grupos


# Uma secao baseada nos veredictos da comparacao (acertou/falhou/surpreendeu/monitorar),
# com o link do meu video que serviu de evidencia.
def _secao_comparacao(linhas: list[str], titulo: str, comparacoes: list) -> None:
    linhas.append(f"## {titulo}")
    linhas.append("")
    if not comparacoes:
        linhas.append("(nenhum)")
        linhas.append("")
        return

    for comparacao in comparacoes:
        linhas.append(
            f"- {comparacao.jogo} | recomendado {comparacao.score_final:.1f} | "
            f"resultado real {comparacao.score_resultado_real:.1f}"
        )
        if comparacao.melhor_video_url:
            linhas.append(f"  - Meu video: {comparacao.melhor_video_url}")
    linhas.append("")


# Secao dos jogos candidatos a repeticao (ja funcionaram comigo e ainda tem janela).
def _secao_repetir(linhas: list[str], candidatos: list) -> None:
    linhas.append("## Jogos para repetir")
    linhas.append("")
    if not candidatos:
        linhas.append("(nenhum)")
        linhas.append("")
        return

    for candidato in candidatos:
        linhas.append(
            f"- {candidato.jogo} | resultado real {candidato.score_resultado_real:.1f} | "
            f"oportunidade {candidato.score_oportunidade:.1f} | "
            f"formato {candidato.tipo_video}"
        )
        linhas.append(f"  - Meu video: {candidato.melhor_video_url}")
    linhas.append("")


# Secao dos formatos que funcionam melhor comigo (media por tipo_video, todos os videos).
def _secao_formatos(linhas: list[str], desempenhos: list) -> None:
    linhas.append("## Formatos que funcionam melhor comigo")
    linhas.append("")
    if not desempenhos:
        linhas.append("(sem dados)")
        linhas.append("")
        return

    for desempenho in desempenhos:
        linhas.append(
            f"- {desempenho.tipo_video} | media {desempenho.media_score:.1f} | "
            f"{desempenho.videos} video(s)"
        )
    linhas.append("")


# Secao do fit real dos principais jogos do ranking (n/d quando nunca testei o jogo).
def _secao_fit_real(linhas: list[str], ranking: list[ResultadoRecomendacao]) -> None:
    linhas.append("## Fit real dos principais jogos")
    linhas.append("")
    principais = sorted(ranking, key=lambda r: r.score_final, reverse=True)[:LIMITE_PRINCIPAIS]
    if not principais:
        linhas.append("(ranking vazio)")
        linhas.append("")
        return

    for resultado in principais:
        fit_real = (
            "n/d" if resultado.score_fit_real is None else f"{resultado.score_fit_real:.1f}"
        )
        linhas.append(
            f"- {resultado.jogo.nome} | final {resultado.score_final:.1f} | fit real {fit_real}"
        )
    linhas.append("")
