# Camada de coleta do YouTube (YouTube Data API v3, via stdlib urllib — sem dependencia).
#
# - coletar_video_por_id: um video por id (com cache opcional).
# - coletar_videos_por_ids: lote a partir de um arquivo de ids.
# - coletar_canal: videos recentes de um canal (via uploads playlist).
# A chave vem da variavel de ambiente YOUTUBE_API_KEY (nunca escrita no codigo).

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from cache_youtube import CACHE_PATH as CACHE_PADRAO, buscar_no_cache, salvar_no_cache
from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from comentario_jogo import pergunta_nome_do_jogo
from config import ler_chave_youtube
from modelos import (
    ComentarioAnalisado,
    ComentariosColetados,
    DetalheVideoYoutube,
    VideoColetado,
)


API_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
API_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
API_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
API_COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
API_COMMENTS_URL = "https://www.googleapis.com/youtube/v3/comments"


# Devolve a chave do ambiente ou levanta RuntimeError com mensagem clara.
def _exigir_chave() -> str:
    chave = ler_chave_youtube()
    if chave is None:
        raise RuntimeError(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de coletar do YouTube (veja .env.example)."
        )
    return chave


# Faz um GET na API e devolve o JSON, convertendo falha de rede em RuntimeError claro.
# Sao dois casos diferentes de URLError: timeout sobe CRU de proposito, porque quem chama
# envolve isso em _com_retentativas_timeout e so consegue reconhecer o timeout no erro
# original; qualquer outra falha (DNS, conexao recusada, cabo na tomada) nao melhora com
# retentativa e ja vira RuntimeError aqui, que e o que os comandos do main.py capturam.
def _get_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=10) as resposta:
            return json.load(resposta)
    except HTTPError as erro:
        raise RuntimeError(
            f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
        ) from erro
    except URLError as erro:
        if _eh_timeout(erro):
            raise
        raise RuntimeError(
            f"Falha de rede ao chamar a YouTube Data API ({erro.reason}). "
            "Verifique a conexao e tente de novo."
        ) from erro


# Executa uma operacao de rede com ate duas novas tentativas quando o problema e timeout.
def _com_retentativas_timeout(funcao, operacao: str, video_id: str = "", tentativas: int = 3):
    ultimo_erro = None
    for _ in range(tentativas):
        try:
            return funcao()
        except Exception as erro:
            if not _eh_timeout(erro):
                raise
            ultimo_erro = erro

    alvo = f" do video {video_id}" if video_id else ""
    raise RuntimeError(
        f"Timeout na operacao {operacao}{alvo} apos {tentativas} tentativas."
    ) from ultimo_erro


# Identifica timeout direto ou encapsulado em URLError.
def _eh_timeout(erro: Exception) -> bool:
    if isinstance(erro, (TimeoutError, SocketTimeout)):
        return True
    if isinstance(erro, URLError) and isinstance(erro.reason, (TimeoutError, SocketTimeout)):
        return True
    return False


# Busca os dados de um video por id e devolve um VideoColetado.
# Se caminho_cache for dado, consulta o cache antes (hit = sem chamada de API) e
# salva o resultado nele. Retorna None se o video nao existir.
def coletar_video_por_id(
    video_id: str, caminho_cache: str | Path | None = None
) -> VideoColetado | None:
    if caminho_cache is not None:
        em_cache = buscar_no_cache(video_id, caminho_cache)
        if em_cache is not None:
            return em_cache

    chave = _exigir_chave()
    parametros = urlencode({"part": "snippet,statistics", "id": video_id, "key": chave})
    url = f"{API_VIDEOS_URL}?{parametros}"
    dados = _com_retentativas_timeout(lambda: _get_json(url), "video", video_id)

    itens = dados.get("items", [])
    if not itens:
        return None

    video = _item_para_video(itens[0], video_id)
    if caminho_cache is not None:
        salvar_no_cache(video_id, video, caminho_cache)
    return video


# Converte um item da resposta da YouTube Data API em VideoColetado.
def _item_para_video(item: dict, video_id: str) -> VideoColetado:
    snippet = item.get("snippet", {})
    estatisticas = item.get("statistics", {})
    return VideoColetado(
        titulo=snippet.get("title", ""),
        canal=snippet.get("channelTitle", ""),
        plataforma="youtube",
        url=f"https://www.youtube.com/watch?v={video_id}",
        views=int(estatisticas.get("viewCount", 0)),
        likes=int(estatisticas.get("likeCount", 0)),
        comentarios=int(estatisticas.get("commentCount", 0)),
        data_publicacao=snippet.get("publishedAt", "")[:10],
        texto_comentarios="",
        origem="youtube",
    )


_DURACAO_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


# Converte a duracao ISO 8601 do YouTube (ex: "PT1M30S") em segundos. Formatos sem
# tempo parseavel (ex: "P0D" de uma live em andamento) viram 0.
def _duracao_iso_para_segundos(duracao: str) -> int:
    correspondencia = _DURACAO_RE.fullmatch(duracao or "")
    if not correspondencia:
        return 0
    horas, minutos, segundos = (int(g) if g else 0 for g in correspondencia.groups())
    return horas * 3600 + minutos * 60 + segundos


# Infere o formato do video: live (se houver sinal), curto (<=60s), longo (>60s) ou
# desconhecido (sem duracao parseavel e sem sinal de live).
def _inferir_tipo_video(duracao_segundos: int, item: dict) -> str:
    estado_live = item.get("snippet", {}).get("liveBroadcastContent", "none")
    if estado_live in ("live", "upcoming") or "liveStreamingDetails" in item:
        return "live"
    if duracao_segundos <= 0:
        return "desconhecido"
    if duracao_segundos <= 60:
        return "curto"
    return "longo"


# Converte um item de videos.list em DetalheVideoYoutube. video_id explicito quando se
# sabe o id pedido (chamada unica); None usa o item["id"] (resposta em lote). Reutiliza
# _item_para_video para os campos em comum com VideoColetado.
def _item_para_detalhe(item: dict, video_id: str | None = None) -> DetalheVideoYoutube:
    if video_id is None:
        video_id = item.get("id", "")
    base = _item_para_video(item, video_id)
    snippet = item.get("snippet", {})
    duracao_segundos = _duracao_iso_para_segundos(
        item.get("contentDetails", {}).get("duration", "")
    )
    return DetalheVideoYoutube(
        video_id=video_id,
        titulo=base.titulo,
        descricao=snippet.get("description", ""),
        tags=snippet.get("tags", []),
        url=base.url,
        views=base.views,
        likes=base.likes,
        comentarios=base.comentarios,
        data_publicacao=base.data_publicacao,
        duracao_segundos=duracao_segundos,
        tipo_video=_inferir_tipo_video(duracao_segundos, item),
        canal=base.canal,
    )


# Converte o detalhe rico em VideoColetado, o modelo que o ranking consome. A conversao
# existe para o caminho de referencia poder usar o coletor em lote (1 unidade por 50) em
# vez de uma chamada por video, e de quebra herdar descricao, tags e tipo_video.
def detalhe_para_video_coletado(detalhe: DetalheVideoYoutube) -> VideoColetado:
    return VideoColetado(
        titulo=detalhe.titulo,
        canal=detalhe.canal,
        plataforma="youtube",
        url=detalhe.url,
        views=detalhe.views,
        likes=detalhe.likes,
        comentarios=detalhe.comentarios,
        data_publicacao=detalhe.data_publicacao,
        # Comentario nao e coletado aqui: ele alimenta descoberta, nao identificacao.
        texto_comentarios="",
        origem="youtube",
        tipo_video=detalhe.tipo_video,
        descricao=detalhe.descricao,
        tags=list(detalhe.tags),
    )


# Busca os detalhes ricos de um video por id (snippet + statistics + contentDetails) e
# devolve um DetalheVideoYoutube com descricao, tags, duracao e tipo_video inferido.
# None se nao existir.
def coletar_detalhe_video(video_id: str) -> DetalheVideoYoutube | None:
    chave = _exigir_chave()
    parametros = urlencode(
        {"part": "snippet,statistics,contentDetails", "id": video_id, "key": chave}
    )
    url = f"{API_VIDEOS_URL}?{parametros}"
    dados = _com_retentativas_timeout(
        lambda: _get_json(url), "detalhes", video_id
    )
    itens = dados.get("items", [])
    if not itens:
        return None
    return _item_para_detalhe(itens[0], video_id)


# Busca os detalhes de varios videos em UMA chamada (videos.list aceita ate 50 ids por
# requisicao, custando 1 unidade de quota para o lote inteiro). Devolve um DetalheVideoYoutube
# por item retornado (videos inexistentes simplesmente nao voltam).
def coletar_detalhes_em_lote(video_ids: list[str]) -> list[DetalheVideoYoutube]:
    if not video_ids:
        return []
    chave = _exigir_chave()
    parametros = urlencode(
        {"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids), "key": chave}
    )
    url = f"{API_VIDEOS_URL}?{parametros}"
    dados = _com_retentativas_timeout(
        lambda: _get_json(url), "detalhes", ",".join(video_ids)
    )
    itens = dados.get("items", [])
    return [_item_para_detalhe(item) for item in itens]


# Busca os detalhes de muitos videos quebrando em lotes de 50 (limite da videos.list).
def coletar_detalhes_em_lote_varios(
    video_ids: list[str], tamanho_lote: int = 50
) -> list[DetalheVideoYoutube]:
    detalhes = []
    for inicio in range(0, len(video_ids), tamanho_lote):
        detalhes.extend(coletar_detalhes_em_lote(video_ids[inicio : inicio + tamanho_lote]))
    return detalhes


# Descobre o id da playlist de uploads de um canal (None se o canal nao existir).
def obter_playlist_uploads(channel_id: str) -> str | None:
    chave = _exigir_chave()
    parametros = urlencode({"part": "contentDetails", "id": channel_id, "key": chave})
    url = f"{API_CHANNELS_URL}?{parametros}"
    dados = _com_retentativas_timeout(lambda: _get_json(url), "canal")
    itens = dados.get("items", [])
    if not itens:
        return None
    return itens[0]["contentDetails"]["relatedPlaylists"]["uploads"]


# Lista os video_ids mais recentes de um canal (via uploads playlist), ate o limite.
def listar_ids_recentes_do_canal(channel_id: str, limite: int = 5) -> list[str]:
    playlist = obter_playlist_uploads(channel_id)
    if playlist is None:
        return []

    chave = _exigir_chave()
    parametros = urlencode(
        {"part": "contentDetails", "playlistId": playlist, "maxResults": limite, "key": chave}
    )
    url = f"{API_PLAYLIST_ITEMS_URL}?{parametros}"
    dados = _com_retentativas_timeout(lambda: _get_json(url), "lista de videos do canal")
    return [item["contentDetails"]["videoId"] for item in dados.get("items", [])]


# Lista TODOS os video_ids do canal, paginando a uploads playlist (50 por pagina, 1 unidade
# de quota por pagina). limite_maximo (opcional) corta a coleta ao atingir N ids — util para
# um teto seguro na primeira coleta. Lista vazia se o canal nao existir.
def listar_todos_ids_do_canal(
    channel_id: str,
    limite_maximo: int | None = None,
    ao_progresso: Callable[[int, int], None] | None = None,
) -> list[str]:
    playlist = obter_playlist_uploads(channel_id)
    if playlist is None:
        return []

    chave = _exigir_chave()
    ids: list[str] = []
    pagina = None
    numero_pagina = 0
    while True:
        parametros = {
            "part": "contentDetails",
            "playlistId": playlist,
            "maxResults": 50,
            "key": chave,
        }
        if pagina:
            parametros["pageToken"] = pagina
        url = f"{API_PLAYLIST_ITEMS_URL}?{urlencode(parametros)}"
        dados = _com_retentativas_timeout(
            lambda: _get_json(url), f"pagina {numero_pagina + 1} de ids do canal"
        )
        numero_pagina += 1

        for item in dados.get("items", []):
            ids.append(item["contentDetails"]["videoId"])
            if limite_maximo is not None and len(ids) >= limite_maximo:
                if ao_progresso is not None:
                    ao_progresso(numero_pagina, len(ids))
                return ids[:limite_maximo]

        if ao_progresso is not None:
            ao_progresso(numero_pagina, len(ids))

        pagina = dados.get("nextPageToken")
        if not pagina:
            return ids


# Lista os videos recentes do canal (uploads playlist) como dicts {video_id, titulo},
# ate o limite. Padrao 10 para gastar pouca quota (channels.list + playlistItems.list =
# 2 unidades, sem buscar estatisticas). Lista vazia se o canal nao existir.
def listar_videos_recentes_do_canal(channel_id: str, limite: int = 10) -> list[dict]:
    playlist = obter_playlist_uploads(channel_id)
    if playlist is None:
        return []

    chave = _exigir_chave()
    parametros = urlencode(
        {
            "part": "snippet,contentDetails",
            "playlistId": playlist,
            "maxResults": limite,
            "key": chave,
        }
    )
    url = f"{API_PLAYLIST_ITEMS_URL}?{parametros}"
    dados = _com_retentativas_timeout(lambda: _get_json(url), "lista de videos do canal")
    return [
        {
            "video_id": item.get("contentDetails", {}).get("videoId", ""),
            "titulo": item.get("snippet", {}).get("title", ""),
        }
        for item in dados.get("items", [])
    ]


# Le os video_ids de um arquivo texto (um por linha), ignorando vazios e repetidos.
def ler_ids_de_arquivo(caminho: str | Path) -> list[str]:
    caminho = Path(caminho)
    if not caminho.exists():
        return []

    ids = []
    vistos = set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        video_id = linha.strip()
        if video_id and video_id not in vistos:
            ids.append(video_id)
            vistos.add(video_id)
    return ids


# Para cada id: busca (com cache) e salva no CSV, contando os resultados.
def _coletar_e_salvar(
    ids: list[str], caminho_destino: str | Path, caminho_cache: str | Path | None
) -> dict[str, int]:
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}
    for video_id in ids:
        try:
            video = coletar_video_por_id(video_id, caminho_cache)
        except RuntimeError:
            resumo["erros"] += 1
            continue
        if video is None:
            resumo["erros"] += 1
            continue

        resumo["encontrados"] += 1
        try:
            adicionar_video_csv(caminho_destino, video)
            resumo["salvos"] += 1
        except VideoDuplicadoError:
            resumo["duplicados"] += 1
        except ValueError:
            resumo["erros"] += 1
    return resumo


# Coleta varios videos a partir de um arquivo de ids e salva cada um no CSV.
def coletar_videos_por_ids(
    caminho_ids: str | Path,
    caminho_destino: str | Path,
    caminho_cache: str | Path | None = CACHE_PADRAO,
) -> dict[str, int]:
    _exigir_chave()
    return _coletar_e_salvar(ler_ids_de_arquivo(caminho_ids), caminho_destino, caminho_cache)


# Coleta os videos recentes de um canal e salva cada um no CSV. videos.list vai em LOTE
# (1 unidade por 50). limite_comentarios > 0 busca tambem os comentarios, que aqui servem a
# UM proposito so: alimentar o score de descoberta ("gente perguntando que jogo e esse").
# A deteccao nao le esse campo — ver detectar_jogos_no_video. Custo: 1 unidade por video.
def coletar_canal(
    channel_id: str,
    caminho_destino: str | Path,
    limite: int = 5,
    caminho_cache: str | Path | None = CACHE_PADRAO,
    forcar: bool = False,
    limite_comentarios: int = 0,
) -> dict[str, int]:
    ids = listar_ids_recentes_do_canal(channel_id, limite)
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    for detalhe in coletar_detalhes_em_lote_varios(ids):
        resumo["encontrados"] += 1
        video = detalhe_para_video_coletado(detalhe)
        if limite_comentarios > 0:
            video.texto_comentarios = " ".join(
                _comentarios_de_referencia(detalhe.video_id, limite_comentarios)
            )
        try:
            adicionar_video_csv(caminho_destino, video, substituir=forcar)
            resumo["salvos"] += 1
        except VideoDuplicadoError:
            resumo["duplicados"] += 1
        except ValueError:
            resumo["erros"] += 1

    # Video pedido e nao devolvido pela API (apagado/privado) conta como erro.
    resumo["erros"] += len(ids) - resumo["encontrados"]
    return resumo


# Comentario e sinal secundario aqui: qualquer erro de API degrada para lista vazia, para
# nao perder o video. limite_respostas baixo de proposito — medicao mostrou que o padrao 20
# dispara cerca de 3 chamadas extras de comments.list por video sem trazer sinal novo, e
# resposta de thread nao e onde a pergunta "que jogo e esse" aparece.
def _comentarios_de_referencia(video_id: str, limite: int) -> list[str]:
    try:
        return coletar_textos_comentarios(video_id, limite, limite_respostas=5).textos
    except RuntimeError:
        return []


# Para cada video recente do canal, busca os detalhes ricos e devolve a lista de
# DetalheVideoYoutube. Nao salva em CSV — so coleta para analise. Padrao 10 (pouca quota).
def coletar_detalhes_do_canal(channel_id: str, limite: int = 10) -> list[DetalheVideoYoutube]:
    detalhes = []
    for video_id in listar_ids_recentes_do_canal(channel_id, limite):
        detalhe = coletar_detalhe_video(video_id)
        if detalhe is not None:
            detalhes.append(detalhe)
    return detalhes


# Detecta o caso "comentarios desativados": a API responde HTTP 403 com reason
# 'commentsDisabled'. Le o corpo do erro para nao confundir com 403 de quota ou chave.
def _comentarios_desativados(erro: HTTPError) -> bool:
    if erro.code != 403:
        return False
    try:
        corpo = json.loads(erro.read().decode("utf-8"))
    except (ValueError, OSError):
        return False
    motivos = {e.get("reason", "") for e in corpo.get("error", {}).get("errors", [])}
    return "commentsDisabled" in motivos


# Le JSON de um endpoint de comentarios preservando o corpo de HTTPError para detectar
# comentarios desativados, mas aplicando retry para timeout. Falha de rede que nao seja
# HTTP vira RuntimeError, igual ao _get_json: sem isso um URLError cru subiria ate o
# terminal como stack trace. O `except HTTPError` vem ANTES do `except URLError` porque
# HTTPError e subclasse de URLError — invertendo a ordem, o corpo do erro se perderia.
def _get_json_comentarios(url: str, operacao: str, video_id: str) -> dict:
    try:
        return _com_retentativas_timeout(
            _ler_json_comentarios(url),
            operacao,
            video_id,
        )
    except HTTPError:
        raise
    except URLError as erro:
        raise RuntimeError(
            f"Falha de rede ao buscar {operacao} do video {video_id} ({erro.reason}). "
            "Verifique a conexao e tente de novo."
        ) from erro


# Monta uma funcao leitora para que o retry possa reabrir a URL a cada tentativa.
def _ler_json_comentarios(url: str):
    def _ler() -> dict:
        with urlopen(url, timeout=10) as resposta:
            return json.load(resposta)

    return _ler


# Coleta textos de comentarios principais e respostas de um video. Nao guarda nenhum dado
# pessoal (autor, canal, foto) — so texto e contagens uteis para diagnostico.
#
# channel_id_dono (opcional) liga a classificacao usada pela deteccao por comentario: o
# authorChannelId que a API manda no snippet e comparado com ele e o resultado vira um
# BOOLEANO. O id do terceiro e lido, usado e descartado dentro desta funcao — o que sai daqui
# em ComentarioAnalisado e so texto, booleanos e um indice sequencial local ao video. Essa e
# a razao de a classificacao morar na coleta e nao no detector: o unico ponto do sistema que
# pode ver o id do autor e este, e ele nao deixa o id escapar.
#
# ordem="relevance" (o padrao da API e "time") porque o limite corta os comentarios: pegando
# os mais relevantes, a pergunta "Nome do jogo?" muito curtida — e a resposta do dono nela —
# entram na fatia coletada, enquanto por data cairiam os comentarios mais novos, que
# costumam ser reacoes soltas. Nao muda o custo: commentThreads custa 1 unidade por chamada
# seja qual for a ordem. Como bonus, o resultado deixa de mudar a cada comentario novo.
def coletar_textos_comentarios(
    video_id: str,
    limite: int = 50,
    limite_respostas: int = 20,
    channel_id_dono: str | None = None,
    ordem: str = "relevance",
) -> ComentariosColetados:
    if limite <= 0:
        return ComentariosColetados()

    chave = _exigir_chave()
    parametros = urlencode(
        {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(limite, 100),
            "textFormat": "plainText",
            "order": ordem,
            "key": chave,
        }
    )
    url = f"{API_COMMENT_THREADS_URL}?{parametros}"
    try:
        dados = _get_json_comentarios(url, "comentarios", video_id)
    except HTTPError as erro:
        if _comentarios_desativados(erro):
            return ComentariosColetados()
        raise RuntimeError(
            f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
        ) from erro

    coleta = ComentariosColetados()
    contexto = _ContextoAutoria(channel_id_dono)

    for item in dados.get("items", []):
        if len(coleta.textos) >= limite:
            coleta.incompleto = True
            break

        snippet_thread = item.get("snippet", {})
        comentario_topo = snippet_thread.get("topLevelComment", {})
        respostas_antes_thread = coleta.respostas
        snippet_topo = comentario_topo.get("snippet", {})
        texto_topo = snippet_topo.get("textDisplay", "")
        if texto_topo:
            coleta.textos.append(texto_topo)
            coleta.comentarios_principais += 1
            coleta.analisados.append(contexto.analisar(snippet_topo, False))

        # A pergunta do topo e o que autoriza ler uma resposta seca ("lava and aqua") como
        # nome de jogo, entao ela e calculada uma vez e vale para a thread inteira.
        pergunta = pergunta_nome_do_jogo(texto_topo)
        respostas_embutidas = item.get("replies", {}).get("comments", [])
        for resposta in respostas_embutidas:
            if len(coleta.textos) >= limite:
                coleta.incompleto = True
                break
            _adicionar_resposta(coleta, resposta, contexto, pergunta)

        total_respostas = int(snippet_thread.get("totalReplyCount", 0) or 0)
        if (
            total_respostas > len(respostas_embutidas)
            and limite_respostas > len(respostas_embutidas)
            and len(coleta.textos) < limite
        ):
            _coletar_respostas_adicionais(
                comentario_topo.get("id", ""),
                video_id,
                chave,
                coleta,
                contexto,
                pergunta,
                limite,
                limite_respostas - len(respostas_embutidas),
            )

        respostas_no_thread = coleta.respostas - respostas_antes_thread
        if total_respostas > respostas_no_thread:
            coleta.incompleto = True

    return coleta


# Mantem a API antiga: quem so precisa de texto continua recebendo list[str].
def coletar_comentarios(video_id: str, limite: int = 50) -> list[str]:
    return coletar_textos_comentarios(video_id, limite).textos


# Estado da coleta de UM video: o que ja foi visto (para nao duplicar resposta) e a traducao
# de autor para um indice anonimo.
#
# A barreira de privacidade do projeto mora aqui. O authorChannelId entra nesta classe,
# vira um booleano ("e o dono?") e um inteiro sequencial local ao video, e some — nao e
# guardado em atributo, nao volta para quem chamou e nao chega perto de CSV, log ou cache.
# O indice existe porque a corroboracao precisa distinguir "duas pessoas disseram o mesmo
# nome" de "uma pessoa disse tres vezes", e para isso basta saber que sao autores
# diferentes; nao e preciso saber QUEM sao.
@dataclass
class _ContextoAutoria:
    channel_id_dono: str | None = None
    ids_vistos: set[str] = field(default_factory=set)
    textos_vistos: set[str] = field(default_factory=set)
    _indices: dict[str, int] = field(default_factory=dict)

    def analisar(self, snippet: dict, responde_pergunta: bool) -> ComentarioAnalisado:
        autor = snippet.get("authorChannelId", {}).get("value", "")
        return ComentarioAnalisado(
            texto=snippet.get("textDisplay", ""),
            do_dono=bool(self.channel_id_dono) and autor == self.channel_id_dono,
            responde_pergunta_de_jogo=responde_pergunta,
            autor_indice=self._indice(autor),
        )

    # Autor sem id vira -1 ("desconhecido"), que a corroboracao trata como um unico autor:
    # sem saber se sao pessoas diferentes, o certo e nao contar como confirmacao.
    def _indice(self, autor: str) -> int:
        if not autor:
            return -1
        return self._indices.setdefault(autor, len(self._indices))


def _adicionar_resposta(
    coleta: ComentariosColetados,
    resposta: dict,
    contexto: _ContextoAutoria,
    responde_pergunta: bool,
) -> None:
    resposta_id = resposta.get("id", "")
    snippet = resposta.get("snippet", {})
    texto = snippet.get("textDisplay", "")
    if not texto:
        return
    if resposta_id and resposta_id in contexto.ids_vistos:
        return
    if not resposta_id and texto in contexto.textos_vistos:
        return

    if resposta_id:
        contexto.ids_vistos.add(resposta_id)
    contexto.textos_vistos.add(texto)
    coleta.textos.append(texto)
    coleta.respostas += 1
    coleta.analisados.append(contexto.analisar(snippet, responde_pergunta))


def _coletar_respostas_adicionais(
    parent_id: str,
    video_id: str,
    chave: str,
    coleta: ComentariosColetados,
    contexto: _ContextoAutoria,
    responde_pergunta: bool,
    limite_total: int,
    limite_respostas: int,
) -> None:
    if not parent_id or limite_respostas <= 0:
        coleta.incompleto = True
        return

    coletadas = 0
    pagina = None
    while len(coleta.textos) < limite_total and coletadas < limite_respostas:
        parametros = {
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": min(100, limite_total - len(coleta.textos), limite_respostas - coletadas),
            "textFormat": "plainText",
            "key": chave,
        }
        if pagina:
            parametros["pageToken"] = pagina

        try:
            dados = _get_json_comentarios(
                f"{API_COMMENTS_URL}?{urlencode(parametros)}",
                "respostas",
                video_id,
            )
        except HTTPError as erro:
            raise RuntimeError(
                f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
            ) from erro

        antes = coleta.respostas
        for resposta in dados.get("items", []):
            if len(coleta.textos) >= limite_total or coletadas >= limite_respostas:
                coleta.incompleto = True
                break
            _adicionar_resposta(coleta, resposta, contexto, responde_pergunta)
            if coleta.respostas > antes:
                coletadas += 1
                antes = coleta.respostas

        pagina = dados.get("nextPageToken")
        if not pagina:
            return

    coleta.incompleto = True
