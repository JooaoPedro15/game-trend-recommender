# Orquestracao da analise do meu proprio canal: junta coleta (coletor_youtube),
# deteccao (detector_jogo) e persistencia (meus_videos) em um unico fluxo.
# Nao tem logica de rede propria — so costura as pecas das sprints anteriores.
#
# Custo de quota: channels.list (1) + playlistItems.list (1) + por video
# videos.list (1) + commentThreads.list (1) = 2 + 2*N. Por isso o limite padrao
# e pequeno. O limite de comentarios NAO afeta quota (commentThreads custa 1 fixo
# por video); controla apenas quanto texto entra na deteccao.

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from coletor_youtube import (
    coletar_detalhe_video,
    coletar_detalhes_em_lote,
    coletar_textos_comentarios,
    listar_ids_recentes_do_canal,
    listar_todos_ids_do_canal,
)
from detector_jogo import DeteccaoJogo, detectar_jogo_em_conteudo
from modelos import ComentariosColetados, DetalheVideoYoutube, JogoSeed, MeuVideo
from meus_videos import salvar_meu_video


# Por quanto tempo o checkpoint de ids continua confiavel. Ele existe para retomar uma
# coleta interrompida sem repaginar a playlist de uploads, e repaginar custa pouco (~1
# unidade de quota por 50 videos). Ja um checkpoint velho ESCONDE todo video publicado
# depois dele, e a coleta fica cega sem avisar ninguem. Os dois erros nao custam a mesma
# coisa, entao a validade e curta de proposito: erra para o lado barato.
VALIDADE_CHECKPOINT_HORAS = 6


# Coleta os videos recentes do canal, detecta o jogo de cada um e salva/atualiza em
# caminho_destino. Recebe `jogos` por parametro (injecao) para nao depender de disco e
# ficar testavel com fakes. Devolve um resumo contavel do que aconteceu.
# Usa a mesma _detectar_com_estrategia da coleta completa: metadado primeiro (de graca,
# ja veio no videos.list) e comentarios so onde ele falhou (1 unidade de quota por video).
# Antes este caminho buscava comentarios sempre — duas logicas de deteccao para o mesmo
# problema, e a duplicada era a que gastava quota a toa.
def analisar_meu_canal(
    channel_id: str,
    jogos: list[JogoSeed],
    caminho_destino: str | Path,
    limite: int = 5,
    limite_comentarios: int = 20,
    comentarios_extra_sem_jogo: int = 0,
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
        deteccao, _por_comentarios, comentarios = _detectar_com_estrategia(
            detalhe, jogos, limite_comentarios, comentarios_extra_sem_jogo
        )
        if not deteccao.detectou:
            resumo["jogos_nao_detectados"] += 1
        else:
            resumo["jogos_detectados"] += 1

        resultado = salvar_meu_video(
            caminho_destino, _montar_meu_video(detalhe, deteccao, comentarios)
        )
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
# forcar=True desliga o passo 2: o cache por id vira uma armadilha quando a linha salva
# esta incompleta (video coletado antes das colunas descricao/tags existirem fica sem
# nenhuma fonte de deteccao e nunca mais e visitado). E a valvula de escape do cache.
def analisar_canal_completo(
    channel_id: str,
    jogos: list[JogoSeed],
    caminho_destino: str | Path,
    ids_existentes: set[str],
    limite_maximo: int | None = None,
    limite_comentarios: int = 20,
    comentarios_extra_sem_jogo: int = 0,
    forcar: bool = False,
    caminho_checkpoint: str | Path | None = None,
    ao_progresso_ids: Callable[[int, int], None] | None = None,
    ao_progresso_lote: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    ids = _obter_ids_com_checkpoint(
        channel_id, limite_maximo, caminho_checkpoint, ao_progresso_ids, forcar=forcar
    )
    novos = ids if forcar else [video_id for video_id in ids if video_id not in ids_existentes]

    resumo = {
        "encontrados": len(ids),
        "em_cache": len(ids) - len(novos),
        "analisados": 0,
        "detectados_sem_comentarios": 0,
        "detectados_por_comentarios": 0,
        "sem_jogo": 0,
        "erros": 0,
    }

    for numero_lote, lote in enumerate(_quebrar_lotes(novos, 50), start=1):
        detalhes = _coletar_detalhes_lote_seguro(lote)
        for detalhe in detalhes:
            resumo["analisados"] += 1
            deteccao, por_comentarios, comentarios = _detectar_com_estrategia(
                detalhe, jogos, limite_comentarios, comentarios_extra_sem_jogo
            )
            if not deteccao.detectou:
                resumo["sem_jogo"] += 1
            elif por_comentarios:
                resumo["detectados_por_comentarios"] += 1
            else:
                resumo["detectados_sem_comentarios"] += 1

            salvar_meu_video(caminho_destino, _montar_meu_video(detalhe, deteccao, comentarios))

        if ao_progresso_lote is not None:
            ao_progresso_lote(numero_lote, resumo["analisados"])

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
) -> tuple[DeteccaoJogo, bool, ComentariosColetados]:
    comentarios = ComentariosColetados()
    deteccao = detectar_jogo_em_conteudo(
        jogos, titulo=detalhe.titulo, descricao=detalhe.descricao, tags=detalhe.tags
    )
    if deteccao.detectou:
        return deteccao, False, comentarios

    if limite_comentarios > 0:
        comentarios = _coletar_comentarios_seguro(detalhe.video_id, limite_comentarios)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=detalhe.titulo,
            descricao=detalhe.descricao,
            tags=detalhe.tags,
            comentarios=comentarios.textos,
        )
        if deteccao.detectou:
            return deteccao, True, comentarios

    if comentarios_extra_sem_jogo > limite_comentarios:
        comentarios = _coletar_comentarios_seguro(detalhe.video_id, comentarios_extra_sem_jogo)
        deteccao = detectar_jogo_em_conteudo(
            jogos,
            titulo=detalhe.titulo,
            descricao=detalhe.descricao,
            tags=detalhe.tags,
            comentarios=comentarios.textos,
        )
        if deteccao.detectou:
            return deteccao, True, comentarios

    return deteccao, False, comentarios


# Busca o detalhe do video; erro de API ou video sumido vira None, sem derrubar o lote.
def _coletar_detalhe_seguro(video_id: str) -> DetalheVideoYoutube | None:
    try:
        return coletar_detalhe_video(video_id)
    except RuntimeError as erro:
        _avisar_erro_coleta(video_id, "detalhes", erro)
        return None


# Busca um lote via videos.list; se o lote falhar, cai para tentativas por video.
def _coletar_detalhes_lote_seguro(video_ids: list[str]) -> list[DetalheVideoYoutube]:
    try:
        return coletar_detalhes_em_lote(video_ids)
    except RuntimeError as erro:
        alvo = ",".join(video_ids)
        _avisar_erro_coleta(alvo, "detalhes em lote", erro)
        detalhes = []
        for video_id in video_ids:
            detalhe = _coletar_detalhe_seguro(video_id)
            if detalhe is not None:
                detalhes.append(detalhe)
        return detalhes


# Comentarios sao sinal secundario: qualquer erro de API degrada para lista vazia, para
# nao perder o video (titulo, descricao e tags ainda permitem detectar o jogo).
def _coletar_comentarios_seguro(video_id: str, limite: int) -> ComentariosColetados:
    try:
        return coletar_textos_comentarios(video_id, limite)
    except RuntimeError as erro:
        _avisar_erro_coleta(video_id, "comentarios", erro)
        return ComentariosColetados(incompleto=True)


# Monta o MeuVideo a partir do detalhe e da deteccao (jogo vazio quando nada detectado).
def _montar_meu_video(
    detalhe: DetalheVideoYoutube,
    deteccao: DeteccaoJogo,
    comentarios: ComentariosColetados | None = None,
) -> MeuVideo:
    comentarios = comentarios or ComentariosColetados()
    jogo = deteccao.jogo_detectado
    status = "jogo_pendente_seed" if deteccao.detectou and not deteccao.jogo_no_seed else "pendente"
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
        status_analise=status,
        descricao=detalhe.descricao,
        tags=detalhe.tags,
        duracao_segundos=detalhe.duracao_segundos,
        motivo_nao_detectado=deteccao.motivo_nao_detectado,
        jogo_no_seed=deteccao.jogo_no_seed,
        comentarios_incompletos=comentarios.incompleto,
        comentarios_coletados=comentarios.comentarios_principais,
        respostas_coletadas=comentarios.respostas,
    )


# Mostra erro recuperavel com video, operacao e tentativas antes de seguir a coleta.
def _avisar_erro_coleta(video_id: str, operacao: str, erro: Exception) -> None:
    print(
        f"AVISO: video {video_id}: operacao {operacao} falhou apos 3 tentativas "
        f"({erro}). A coleta continuara."
    )


# Divide listas em fatias para processar e salvar resultados parciais por lote.
def _quebrar_lotes(itens: list[str], tamanho: int):
    for inicio in range(0, len(itens), tamanho):
        yield itens[inicio : inicio + tamanho]


# Usa checkpoint de IDs quando compativel; caso contrario pagina o canal e salva novo checkpoint.
def _obter_ids_com_checkpoint(
    channel_id: str,
    limite_maximo: int | None,
    caminho_checkpoint: str | Path | None,
    ao_progresso_ids: Callable[[int, int], None] | None,
    forcar: bool = False,
) -> list[str]:
    ids_checkpoint = _carregar_checkpoint_ids(
        caminho_checkpoint, channel_id, limite_maximo, forcar
    )
    if ids_checkpoint is not None:
        return ids_checkpoint

    ids = listar_todos_ids_do_canal(channel_id, limite_maximo, ao_progresso_ids)
    _salvar_checkpoint_ids(caminho_checkpoint, channel_id, limite_maximo, ids)
    return ids


# Carrega checkpoint sem credenciais, validando canal, teto da coleta e validade. Com
# forcar o checkpoint e descartado mesmo dentro do prazo: quem pede recoleta quer a lista
# de ids de agora, nao a que estava guardada no disco.
def _carregar_checkpoint_ids(
    caminho_checkpoint: str | Path | None,
    channel_id: str,
    limite_maximo: int | None,
    forcar: bool = False,
) -> list[str] | None:
    if caminho_checkpoint is None or forcar:
        return None
    caminho = Path(caminho_checkpoint)
    if not caminho.exists():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if dados.get("channel_id") != channel_id or dados.get("limite_maximo") != limite_maximo:
        return None
    if _checkpoint_vencido(dados.get("salvo_em")):
        return None
    ids = dados.get("video_ids", [])
    if not isinstance(ids, list):
        return None
    return [str(video_id) for video_id in ids if str(video_id).strip()]


# Um checkpoint so vale por VALIDADE_CHECKPOINT_HORAS. Sem data, ou com data ilegivel,
# ele conta como vencido: na duvida repaginar (barato) e melhor que confiar (arriscado).
def _checkpoint_vencido(salvo_em: object) -> bool:
    try:
        data_salvo = datetime.fromisoformat(str(salvo_em))
    except (TypeError, ValueError):
        return True

    return datetime.now() - data_salvo > timedelta(hours=VALIDADE_CHECKPOINT_HORAS)


# Salva somente IDs e metadados operacionais, nunca chave de API.
def _salvar_checkpoint_ids(
    caminho_checkpoint: str | Path | None,
    channel_id: str,
    limite_maximo: int | None,
    ids: list[str],
) -> None:
    if caminho_checkpoint is None:
        return
    caminho = Path(caminho_checkpoint)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = {
        "channel_id": channel_id,
        "limite_maximo": limite_maximo,
        "video_ids": ids,
        "total": len(ids),
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
