# Camada de coleta do YouTube (YouTube Data API v3, via stdlib urllib — sem dependencia).
#
# - coletar_video_por_id: um video por id (com cache opcional).
# - coletar_videos_por_ids: lote a partir de um arquivo de ids.
# - coletar_canal: videos recentes de um canal (via uploads playlist).
# A chave vem da variavel de ambiente YOUTUBE_API_KEY (nunca escrita no codigo).

import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from cache_youtube import CACHE_PATH as CACHE_PADRAO, buscar_no_cache, salvar_no_cache
from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from config import ler_chave_youtube
from modelos import DetalheVideoYoutube, VideoColetado


API_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
API_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
API_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
API_COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


# Devolve a chave do ambiente ou levanta RuntimeError com mensagem clara.
def _exigir_chave() -> str:
    chave = ler_chave_youtube()
    if chave is None:
        raise RuntimeError(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de coletar do YouTube (veja .env.example)."
        )
    return chave


# Faz um GET na API e devolve o JSON; converte erro HTTP em RuntimeError claro.
def _get_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=10) as resposta:
            return json.load(resposta)
    except HTTPError as erro:
        raise RuntimeError(
            f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
        ) from erro


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
    dados = _get_json(f"{API_VIDEOS_URL}?{parametros}")

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
    )


# Busca os detalhes ricos de um video por id (snippet + statistics + contentDetails) e
# devolve um DetalheVideoYoutube com descricao, tags, duracao e tipo_video inferido.
# None se nao existir.
def coletar_detalhe_video(video_id: str) -> DetalheVideoYoutube | None:
    chave = _exigir_chave()
    parametros = urlencode(
        {"part": "snippet,statistics,contentDetails", "id": video_id, "key": chave}
    )
    itens = _get_json(f"{API_VIDEOS_URL}?{parametros}").get("items", [])
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
    itens = _get_json(f"{API_VIDEOS_URL}?{parametros}").get("items", [])
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
    itens = _get_json(f"{API_CHANNELS_URL}?{parametros}").get("items", [])
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
    itens = _get_json(f"{API_PLAYLIST_ITEMS_URL}?{parametros}").get("items", [])
    return [item["contentDetails"]["videoId"] for item in itens]


# Lista TODOS os video_ids do canal, paginando a uploads playlist (50 por pagina, 1 unidade
# de quota por pagina). limite_maximo (opcional) corta a coleta ao atingir N ids — util para
# um teto seguro na primeira coleta. Lista vazia se o canal nao existir.
def listar_todos_ids_do_canal(
    channel_id: str, limite_maximo: int | None = None
) -> list[str]:
    playlist = obter_playlist_uploads(channel_id)
    if playlist is None:
        return []

    chave = _exigir_chave()
    ids: list[str] = []
    pagina = None
    while True:
        parametros = {
            "part": "contentDetails",
            "playlistId": playlist,
            "maxResults": 50,
            "key": chave,
        }
        if pagina:
            parametros["pageToken"] = pagina
        dados = _get_json(f"{API_PLAYLIST_ITEMS_URL}?{urlencode(parametros)}")

        for item in dados.get("items", []):
            ids.append(item["contentDetails"]["videoId"])
            if limite_maximo is not None and len(ids) >= limite_maximo:
                return ids[:limite_maximo]

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
    itens = _get_json(f"{API_PLAYLIST_ITEMS_URL}?{parametros}").get("items", [])
    return [
        {
            "video_id": item.get("contentDetails", {}).get("videoId", ""),
            "titulo": item.get("snippet", {}).get("title", ""),
        }
        for item in itens
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


# Coleta os videos recentes de um canal (uploads playlist) e salva cada um no CSV.
def coletar_canal(
    channel_id: str,
    caminho_destino: str | Path,
    limite: int = 5,
    caminho_cache: str | Path | None = CACHE_PADRAO,
) -> dict[str, int]:
    ids = listar_ids_recentes_do_canal(channel_id, limite)
    return _coletar_e_salvar(ids, caminho_destino, caminho_cache)


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


# Coleta ate `limite` comentarios de topo (apenas o texto) de um video, via
# commentThreads.list. Nao guarda nenhum dado pessoal (autor, canal, foto) — so o texto,
# que ajuda a detectar o nome do jogo. Sem paginacao: no maximo uma pagina por video.
# Comentarios desativados -> lista vazia, sem quebrar a coleta dos outros videos.
def coletar_comentarios(video_id: str, limite: int = 50) -> list[str]:
    chave = _exigir_chave()
    parametros = urlencode(
        {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(limite, 100),
            "textFormat": "plainText",
            "key": chave,
        }
    )
    url = f"{API_COMMENT_THREADS_URL}?{parametros}"
    try:
        with urlopen(url, timeout=10) as resposta:
            dados = json.load(resposta)
    except HTTPError as erro:
        if _comentarios_desativados(erro):
            return []
        raise RuntimeError(
            f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
        ) from erro

    comentarios = []
    for item in dados.get("items", [])[:limite]:
        texto = (
            item.get("snippet", {})
            .get("topLevelComment", {})
            .get("snippet", {})
            .get("textDisplay", "")
        )
        if texto:
            comentarios.append(texto)
    return comentarios
