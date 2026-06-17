# Relatorio executivo do dia (Sprint 10.4): um Markdown curto com o que importa para
# decidir os proximos jogos a testar. So compoe blocos que ja existem (ranking,
# oportunidades, repetir 9.5, falhos 9.6, evidencias de criadores, meus videos sem jogo):
# aritmetica e formatacao, sem IA. Apenas diagnostico e links; nunca cria roteiro,
# gancho, angulo ou tom de voz.

from pathlib import Path

from evidencias_jogo import gerar_evidencias, resumir_evidencia_criadores
from jogos_falhos import jogos_que_nao_funcionaram
from ranker import filtrar_oportunidades
from repetir_jogos import jogos_para_repetir
from modelos import CanalReferencia, MeuVideo, ResultadoRecomendacao


# Quantos jogos mostrar nas secoes de evidencia/links (mantem o relatorio curto).
LIMITE_EVIDENCIAS = 3


# Gera o relatorio diario em Markdown a partir do ranking atual, dos meus videos e dos
# canais de referencia. Funcao de formatacao: leitura dos dados e timestamp ficam no main.
def gerar_relatorio_diario_markdown(
    caminho: str | Path,
    ranking: list[ResultadoRecomendacao],
    meus_videos: list[MeuVideo],
    canais: list[CanalReferencia],
) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    oportunidades = filtrar_oportunidades(ranking)
    candidatos_repetir = jogos_para_repetir(ranking, meus_videos)
    falhos = jogos_que_nao_funcionaram(ranking, meus_videos)
    sem_jogo = sorted(
        (v for v in meus_videos if not v.jogo_detectado.strip()),
        key=lambda v: v.views,
        reverse=True,
    )
    evidencias_por_jogo = gerar_evidencias(ranking, canais)
    principais = sorted(
        ranking, key=lambda r: r.score_evidencia_criadores, reverse=True
    )[:LIMITE_EVIDENCIAS]

    linhas = ["# Relatorio Diario", ""]
    linhas.append("Resumo do dia para decidir os proximos jogos a testar.")
    linhas.append("")

    _secao_top_jogos(linhas, ranking)
    _secao_oportunidades(linhas, oportunidades)
    _secao_repetir(linhas, candidatos_repetir)
    _secao_falhos(linhas, falhos)
    _secao_sem_jogo(linhas, sem_jogo)
    _secao_evidencias(linhas, principais, evidencias_por_jogo)
    _secao_links(linhas, principais, evidencias_por_jogo)
    _secao_observacoes(linhas, oportunidades, candidatos_repetir, falhos, sem_jogo, meus_videos)

    caminho.write_text("\n".join(linhas), encoding="utf-8")


def _secao_top_jogos(linhas: list[str], ranking: list[ResultadoRecomendacao]) -> None:
    linhas.append("## Top jogos recomendados")
    linhas.append("")
    if not ranking:
        linhas.append("(ranking vazio)")
        linhas.append("")
        return
    for resultado in ranking:
        formato = resultado.formato_sugerido or "n/d"
        linhas.append(
            f"- {resultado.jogo.nome} | final {resultado.score_final:.1f} | "
            f"acao: {resultado.acao_recomendada} | formato: {formato}"
        )
    linhas.append("")


def _secao_oportunidades(linhas: list[str], oportunidades: list) -> None:
    linhas.append("## Top oportunidades")
    linhas.append("")
    if not oportunidades:
        linhas.append("(nenhuma no momento)")
        linhas.append("")
        return
    for posicao, resultado in oportunidades:
        linhas.append(
            f"- #{posicao} {resultado.jogo.nome} | "
            f"oportunidade {resultado.score_oportunidade:.1f} | acao: {resultado.acao_recomendada}"
        )
    linhas.append("")


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
            f"formato {candidato.tipo_video}"
        )
        linhas.append(f"  - {candidato.melhor_video_url}")
    linhas.append("")


def _secao_falhos(linhas: list[str], falhos: list) -> None:
    linhas.append("## Jogos que prometiam mas nao funcionaram")
    linhas.append("")
    if not falhos:
        linhas.append("(nenhum)")
        linhas.append("")
        return
    for falho in falhos:
        linhas.append(
            f"- {falho.jogo} | resultado real {falho.score_resultado_real:.1f} | {falho.conclusao}"
        )
    linhas.append("")


def _secao_sem_jogo(linhas: list[str], sem_jogo: list[MeuVideo]) -> None:
    linhas.append("## Meus videos sem jogo detectado")
    linhas.append("")
    if not sem_jogo:
        linhas.append("(nenhum)")
        linhas.append("")
        return
    for video in sem_jogo:
        linhas.append(f"- {video.titulo} | {video.views} views")
        linhas.append(f"  - {video.url}")
    linhas.append("")


def _secao_evidencias(linhas: list[str], principais: list, evidencias_por_jogo: dict) -> None:
    linhas.append("## Evidencias principais de criadores")
    linhas.append("")
    teve = False
    for resultado in principais:
        evidencias = evidencias_por_jogo.get(resultado.jogo.nome, [])
        if not evidencias:
            continue
        teve = True
        linhas.append(
            f"- {resultado.jogo.nome} (evidencia {resultado.score_evidencia_criadores:.1f}): "
            f"{resumir_evidencia_criadores(evidencias)}"
        )
    if not teve:
        linhas.append("(sem evidencias coletadas)")
    linhas.append("")


def _secao_links(linhas: list[str], principais: list, evidencias_por_jogo: dict) -> None:
    linhas.append("## Links uteis para assistir")
    linhas.append("")
    teve = False
    for resultado in principais:
        evidencias = evidencias_por_jogo.get(resultado.jogo.nome, [])
        if not evidencias:
            continue
        teve = True
        linhas.append(f"- {resultado.jogo.nome}: {evidencias[0].url}")
    if not teve:
        linhas.append("(sem links)")
    linhas.append("")


def _secao_observacoes(
    linhas: list[str],
    oportunidades: list,
    candidatos_repetir: list,
    falhos: list,
    sem_jogo: list,
    meus_videos: list,
) -> None:
    linhas.append("## Observacoes operacionais")
    linhas.append("")
    observacoes = []
    if candidatos_repetir:
        observacoes.append(
            f"{len(candidatos_repetir)} jogo(s) ja funcionaram comigo e valem repetir."
        )
    if falhos:
        observacoes.append(
            f"Cuidado: {len(falhos)} jogo(s) bombaram fora mas falharam comigo."
        )
    if sem_jogo:
        observacoes.append(
            f"{len(sem_jogo)} video(s) seu(s) sem jogo detectado - rode meus_videos_sem_jogo."
        )
    if oportunidades:
        _, topo = oportunidades[0]
        observacoes.append(f"Maior oportunidade agora: {topo.jogo.nome}.")
    if not meus_videos:
        observacoes.append("Sem dados do meu canal ainda - rode coletar_meu_canal para calibrar.")
    if not observacoes:
        observacoes.append("Nada urgente hoje.")

    for observacao in observacoes:
        linhas.append(f"- {observacao}")
    linhas.append("")
