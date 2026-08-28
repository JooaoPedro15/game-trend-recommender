# Redeteccao offline dos meus videos: recalcula o jogo de cada linha ja salva em
# meus_videos.csv usando o texto que o proprio arquivo guarda (titulo, descricao, tags).
# Nao usa rede e nao gasta uma unidade de quota — o texto ja e nosso.
#
# Existe porque a deteccao sempre esteve grudada na coleta: cadastrar um jogo ou um alias
# nao reprocessava nada (o efeito so aparecia na proxima coleta paga), e corrigir a
# deteccao nao consertava sozinho as linhas ja gravadas com o resultado antigo.
#
# REGRA CENTRAL — nunca rebaixar. O CSV guarda as contagens de comentarios, nao o texto
# deles. Uma deteccao que veio de comentarios NAO pode ser conferida aqui, entao quando o
# metadado nao acha nada a linha fica como esta. So limpamos o que veio de uma fonte que
# conseguimos reproduzir (descricao, tags, titulo): se o texto nao sustenta mais o jogo,
# ele sai. Sem isso, uma redeteccao apagaria deteccoes que so a rede poderia recuperar.

from dataclasses import dataclass
from pathlib import Path

from detector_jogo import DeteccaoJogo, detectar_jogo_em_conteudo
from leitor_csv import _ler_linhas
from meus_videos import (
    _bool_para_sim_nao,
    _linha_para_meu_video,
    _reescrever_csv,
)
from modelos import JogoSeed


# Fontes cujo texto esta salvo no CSV e portanto podem ser recalculadas aqui.
FONTES_REPRODUZIVEIS = ("descricao", "tags", "titulo")

# Status que a propria deteccao define. Qualquer outro foi escolhido por uma pessoa e nao
# pode ser sobrescrito por um recalculo.
STATUS_DERIVADOS = ("pendente", "jogo_pendente_seed")


# Uma linha que a redeteccao mudaria (ou mudou), para relatorio e para o modo simulacao.
# acao: detectado (nao tinha jogo e passou a ter) | removido (tinha e o texto nao sustenta
# mais) | trocado (mudou de jogo) | atualizado (mesmo jogo, mas confianca/fonte/presenca no
# seed mudaram — e o caso de cadastrar o jogo depois da coleta).
@dataclass
class MudancaDeteccao:
    video_id: str
    titulo: str
    jogo_antes: str
    jogo_depois: str
    acao: str


# Recalcula a deteccao de todas as linhas do CSV e grava o resultado. Com simular=True
# calcula e relata sem escrever nada. Devolve (resumo, mudancas).
def aplicar_redeteccao(
    caminho: str | Path, jogos: list[JogoSeed], simular: bool = False
) -> tuple[dict[str, int], list[MudancaDeteccao]]:
    caminho = Path(caminho)
    linhas = _ler_linhas(caminho)
    resumo = {
        "analisados": len(linhas),
        "detectados": 0,
        "removidos": 0,
        "trocados": 0,
        "atualizados": 0,
        "preservados": 0,
    }
    mudancas: list[MudancaDeteccao] = []

    for linha in linhas:
        video = _linha_para_meu_video(linha)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=video.titulo,
            descricao=video.descricao,
            tags=video.tags,
        )
        antes = video.jogo_detectado.strip()
        depois = deteccao.jogo_detectado.strip()

        # Metadado nao achou nada e a deteccao salva veio de comentarios: sem o texto dos
        # comentarios nao ha como conferir, entao a linha fica intacta.
        if not depois and antes and video.fonte_deteccao not in FONTES_REPRODUZIVEIS:
            resumo["preservados"] += 1
            continue

        # Comparar so o nome do jogo nao basta: cadastrar o jogo no seed depois da coleta
        # mantem o nome e muda jogo_no_seed, e a linha precisa ser reescrita do mesmo jeito.
        mudou_nome = depois != antes
        mudou_contexto = (
            deteccao.confianca != video.confianca_jogo
            or deteccao.fonte != video.fonte_deteccao
            or deteccao.jogo_no_seed != video.jogo_no_seed
        )
        if not mudou_nome and not mudou_contexto:
            continue

        acao = _classificar(antes, depois, mudou_nome)
        resumo[f"{acao}s"] += 1
        mudancas.append(MudancaDeteccao(video.video_id, video.titulo, antes, depois, acao))
        _gravar_deteccao(linha, deteccao)

    if mudancas and not simular:
        _reescrever_csv(caminho, linhas)

    return resumo, mudancas


# Nomeia o que aconteceu com a linha, para o resumo e para a listagem do terminal.
def _classificar(antes: str, depois: str, mudou_nome: bool) -> str:
    if not mudou_nome:
        return "atualizado"
    if not antes:
        return "detectado"
    if not depois:
        return "removido"
    return "trocado"


# Escreve na linha apenas o que a deteccao decide. data_coleta, views e o resto nao sao
# tocados: nada foi coletado, so recalculado.
def _gravar_deteccao(linha: dict, deteccao: DeteccaoJogo) -> None:
    linha["jogo_detectado"] = deteccao.jogo_detectado
    linha["confianca_jogo"] = deteccao.confianca
    linha["fonte_deteccao"] = deteccao.fonte
    linha["motivo_nao_detectado"] = deteccao.motivo_nao_detectado
    linha["jogo_no_seed"] = _bool_para_sim_nao(deteccao.jogo_no_seed)
    linha["status_analise"] = _status_apos_redeteccao(
        linha.get("status_analise", ""), deteccao
    )


# Status derivado da deteccao e recalculado (e o ponto de redetectar); status escolhido por
# uma pessoa ("analisado", por exemplo) e mantido.
def _status_apos_redeteccao(salvo: str, deteccao: DeteccaoJogo) -> str:
    salvo = (salvo or "").strip()
    if salvo and salvo not in STATUS_DERIVADOS:
        return salvo

    if deteccao.detectou and not deteccao.jogo_no_seed:
        return "jogo_pendente_seed"
    return "pendente"


# Mostra o resultado da redeteccao no terminal, listando as primeiras mudancas.
def imprimir_redeteccao(
    resumo: dict[str, int], mudancas: list[MudancaDeteccao], limite: int = 15
) -> None:
    print("=== Redeteccao dos Meus Videos ===")
    print()
    print(f"Videos analisados: {resumo['analisados']}")
    print(f"Jogo detectado agora: {resumo['detectados']}")
    print(f"Deteccao removida (texto nao sustenta mais): {resumo['removidos']}")
    print(f"Jogo trocado: {resumo['trocados']}")
    print(f"Mesmo jogo, contexto atualizado (ex: entrou no seed): {resumo['atualizados']}")
    print(f"Preservados (deteccao veio de comentarios): {resumo['preservados']}")

    if not mudancas:
        print()
        print("Nenhuma linha mudou.")
        return

    print()
    print(f"Mudancas ({min(limite, len(mudancas))} de {len(mudancas)}):")
    for mudanca in mudancas[:limite]:
        antes = mudanca.jogo_antes or "(nenhum)"
        depois = mudanca.jogo_depois or "(nenhum)"
        print(f"- [{mudanca.acao}] {mudanca.titulo[:55]}")
        print(f"    {antes} -> {depois}")
