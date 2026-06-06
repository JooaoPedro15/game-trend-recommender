# Camada de coleta do YouTube.
#
# coletar_video_por_id ja faz requisicao real a YouTube Data API v3.
# coletar_videos_canal ainda e um stub (sera implementado em etapa futura).
# A chave vem da variavel de ambiente YOUTUBE_API_KEY (nunca escrita no codigo).
# Usa apenas a biblioteca padrao (urllib + json) — sem dependencia externa.

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from config import ler_chave_youtube
from modelos import VideoColetado


API_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


# Busca os dados de um video do YouTube por id e devolve um VideoColetado.
# Retorna None se o video nao existir. Levanta RuntimeError se a chave estiver
# ausente ou se a API responder com erro.
def coletar_video_por_id(video_id: str) -> VideoColetado | None:
    chave = ler_chave_youtube()
    if chave is None:
        raise RuntimeError(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de coletar do YouTube (veja .env.example)."
        )

    parametros = urlencode({"part": "snippet,statistics", "id": video_id, "key": chave})
    url = f"{API_VIDEOS_URL}?{parametros}"

    try:
        with urlopen(url, timeout=10) as resposta:
            dados = json.load(resposta)
    except HTTPError as erro:
        raise RuntimeError(
            f"Erro na YouTube Data API (HTTP {erro.code}). Verifique a chave e a quota."
        ) from erro

    itens = dados.get("items", [])
    if not itens:
        return None

    return _item_para_video(itens[0], video_id)


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


# Coleta os videos mais recentes de um canal do YouTube. Ainda nao implementado.
def coletar_videos_canal(canal_id: str, limite: int) -> list[VideoColetado]:
    raise NotImplementedError(
        "Coleta por canal ainda nao implementada. "
        "Sera adicionada em uma etapa futura usando a YouTube Data API v3."
    )


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


# Coleta varios videos por id (reusando coletar_video_por_id) e salva cada um no CSV.
# Retorna as contagens: lidos, encontrados, salvos, duplicados, erros.
def coletar_videos_por_ids(
    caminho_ids: str | Path, caminho_destino: str | Path
) -> dict[str, int]:
    if ler_chave_youtube() is None:
        raise RuntimeError(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de coletar do YouTube (veja .env.example)."
        )

    ids = ler_ids_de_arquivo(caminho_ids)
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    for video_id in ids:
        try:
            video = coletar_video_por_id(video_id)
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
