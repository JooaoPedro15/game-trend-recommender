# Camada de coleta do YouTube (YouTube Data API v3, via stdlib urllib — sem dependencia).
#
# - coletar_video_por_id: um video por id (com cache opcional).
# - coletar_videos_por_ids: lote a partir de um arquivo de ids.
# - coletar_canal: videos recentes de um canal (via uploads playlist).
# A chave vem da variavel de ambiente YOUTUBE_API_KEY (nunca escrita no codigo).

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from cache_youtube import CACHE_PATH as CACHE_PADRAO, buscar_no_cache, salvar_no_cache
from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from config import ler_chave_youtube
from modelos import VideoColetado


API_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
API_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
API_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


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
    )


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
