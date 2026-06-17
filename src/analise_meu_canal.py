# Orquestracao da analise do meu proprio canal: junta coleta (coletor_youtube),
# deteccao (detector_jogo) e persistencia (meus_videos) em um unico fluxo.
# Nao tem logica de rede propria — so costura as pecas das sprints anteriores.
#
# Custo de quota: channels.list (1) + playlistItems.list (1) + por video
# videos.list (1) + commentThreads.list (1) = 2 + 2*N. Por isso o limite padrao
# e pequeno. O limite de comentarios NAO afeta quota (commentThreads custa 1 fixo
# por video); controla apenas quanto texto entra na deteccao.

from pathlib import Path

from coletor_youtube import (
    coletar_comentarios,
    coletar_detalhe_video,
    coletar_detalhes_em_lote_varios,
    listar_ids_recentes_do_canal,
    listar_todos_ids_do_canal,
)
from detector_jogo import DeteccaoJogo, detectar_jogo_em_conteudo
from modelos import DetalheVideoYoutube, JogoSeed, MeuVideo
from meus_videos import salvar_meu_video


# Coleta os videos recentes do canal, detecta o jogo de cada um e salva/atualiza em
# caminho_destino. Recebe `jogos` por parametro (injecao) para nao depender de disco e
# ficar testavel com fakes. Devolve um resumo contavel do que aconteceu.
def analisar_meu_canal(
    channel_id: str,
    jogos: list[JogoSeed],
    caminho_destino: str | Path,
    limite: int = 5,
    limite_comentarios: int = 20,
) -> dict[str, int]:
    resumo = {
        "analisados": 0,
        "jogos_detectados": 0,
        "jogos_nao_detectados": 0,
        "novos": 0,
        "atualizados": 0,
        "erros": 0,
    }

    for video_id in listar_ids_recentes_do_canal(channel_id, limite):
        detalhe = _coletar_detalhe_seguro(video_id)
        if detalhe is None:
            resumo["erros"] += 1
            continue

        resumo["analisados"] += 1
        comentarios = _coletar_comentarios_seguro(video_id, limite_comentarios)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=detalhe.titulo,
            descricao=detalhe.descricao,
            tags=detalhe.tags,
            comentarios=comentarios,
        )
        if deteccao.jogo is None:
            resumo["jogos_nao_detectados"] += 1
        else:
            resumo["jogos_detectados"] += 1

        resultado = salvar_meu_video(caminho_destino, _montar_meu_video(detalhe, deteccao))
        resumo["novos" if resultado == "criado" else "atualizados"] += 1

    return resumo


# Coleta INTELIGENTE de todos os videos do canal, economizando quota (Sprint 10.9):
#   1. lista todos os ids (paginado)        -> ~1 unidade por 50 videos
#   2. pula os ja salvos (ids_existentes)    -> cache, custo zero nos antigos
#   3. detalhes em LOTE (50 por chamada)     -> ~1 unidade por 50 videos
#   4. detecta por descricao/tags/titulo     -> 0 unidade (ja temos o detalhe)
#   5. so nos NAO detectados: comentarios limitados (1 unidade/video)
#   6. so nos AINDA sem jogo: comentarios extra      (1 unidade/video)
# Assim o comentario, que e o gasto caro, so e buscado onde o metadado falhou.
# ids_existentes (injetado) sao os video_ids ja em meus_videos.csv. Devolve um resumo
# com o progresso. limite_maximo opcional poe um teto na quantidade de videos.
def analisar_canal_completo(
    channel_id: str,
    jogos: list[JogoSeed],
    caminho_destino: str | Path,
    ids_existentes: set[str],
    limite_maximo: int | None = None,
    limite_comentarios: int = 20,
    comentarios_extra_sem_jogo: int = 0,
) -> dict[str, int]:
    ids = listar_todos_ids_do_canal(channel_id, limite_maximo)
    novos = [video_id for video_id in ids if video_id not in ids_existentes]

    resumo = {
        "encontrados": len(ids),
        "em_cache": len(ids) - len(novos),
        "analisados": 0,
        "detectados_sem_comentarios": 0,
        "detectados_por_comentarios": 0,
        "sem_jogo": 0,
        "erros": 0,
    }

    for detalhe in coletar_detalhes_em_lote_varios(novos):
        resumo["analisados"] += 1
        deteccao, por_comentarios = _detectar_com_estrategia(
            detalhe, jogos, limite_comentarios, comentarios_extra_sem_jogo
        )
        if deteccao.jogo is None:
            resumo["sem_jogo"] += 1
        elif por_comentarios:
            resumo["detectados_por_comentarios"] += 1
        else:
            resumo["detectados_sem_comentarios"] += 1

        salvar_meu_video(caminho_destino, _montar_meu_video(detalhe, deteccao))

    # Videos pedidos mas nao retornados pela API (apagados/privados) contam como erro.
    resumo["erros"] = len(novos) - resumo["analisados"]
    return resumo


# Aplica a estrategia de deteccao economica e devolve (deteccao, detectado_por_comentarios):
# primeiro tenta so o metadado (gratis); so se falhar busca comentarios limitados; so se
# ainda assim falhar busca comentarios extra (quando habilitado).
def _detectar_com_estrategia(
    detalhe: DetalheVideoYoutube,
    jogos: list[JogoSeed],
    limite_comentarios: int,
    comentarios_extra_sem_jogo: int,
) -> tuple[DeteccaoJogo, bool]:
    deteccao = detectar_jogo_em_conteudo(
        jogos, titulo=detalhe.titulo, descricao=detalhe.descricao, tags=detalhe.tags
    )
    if deteccao.jogo is not None:
        return deteccao, False

    if limite_comentarios > 0:
        comentarios = _coletar_comentarios_seguro(detalhe.video_id, limite_comentarios)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=detalhe.titulo,
            descricao=detalhe.descricao,
            tags=detalhe.tags,
            comentarios=comentarios,
        )
        if deteccao.jogo is not None:
            return deteccao, True

    if comentarios_extra_sem_jogo > limite_comentarios:
        comentarios = _coletar_comentarios_seguro(detalhe.video_id, comentarios_extra_sem_jogo)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=detalhe.titulo,
            descricao=detalhe.descricao,
            tags=detalhe.tags,
            comentarios=comentarios,
        )
        if deteccao.jogo is not None:
            return deteccao, True

    return deteccao, False


# Busca o detalhe do video; erro de API ou video sumido vira None, sem derrubar o lote.
def _coletar_detalhe_seguro(video_id: str) -> DetalheVideoYoutube | None:
    try:
        return coletar_detalhe_video(video_id)
    except RuntimeError:
        return None


# Comentarios sao sinal secundario: qualquer erro de API degrada para lista vazia, para
# nao perder o video (titulo, descricao e tags ainda permitem detectar o jogo).
def _coletar_comentarios_seguro(video_id: str, limite: int) -> list[str]:
    try:
        return coletar_comentarios(video_id, limite)
    except RuntimeError:
        return []


# Monta o MeuVideo a partir do detalhe e da deteccao (jogo vazio quando nada detectado).
def _montar_meu_video(detalhe: DetalheVideoYoutube, deteccao: DeteccaoJogo) -> MeuVideo:
    jogo = deteccao.jogo.nome if deteccao.jogo is not None else ""
    return MeuVideo(
        video_id=detalhe.video_id,
        titulo=detalhe.titulo,
        url=detalhe.url,
        data_publicacao=detalhe.data_publicacao,
        jogo_detectado=jogo,
        confianca_jogo=deteccao.confianca,
        fonte_deteccao=deteccao.fonte,
        views=detalhe.views,
        likes=detalhe.likes,
        comentarios=detalhe.comentarios,
        tipo_video=detalhe.tipo_video,
    )
