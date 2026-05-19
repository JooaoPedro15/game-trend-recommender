import csv
from pathlib import Path

from leitor_csv import ler_videos_coletados
from modelos import VideoColetado


CAMPOS_VIDEO = [
    "titulo",
    "canal",
    "plataforma",
    "url",
    "views",
    "likes",
    "comentarios",
    "data_publicacao",
    "texto_comentarios",
]


class VideoDuplicadoError(ValueError):
    pass


def adicionar_video_csv(caminho: str | Path, video: VideoColetado) -> None:
    caminho = Path(caminho)
    _validar_video(video)
    _garantir_csv(caminho)

    videos_existentes = ler_videos_coletados(caminho)
    urls_existentes = {_normalizar_url(video_existente.url) for video_existente in videos_existentes}

    if _normalizar_url(video.url) in urls_existentes:
        raise VideoDuplicadoError("Ja existe um video cadastrado com essa URL.")

    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO)
        escritor.writerow(_video_para_linha(video))


def _garantir_csv(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.stat().st_size > 0:
        return

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO)
        escritor.writeheader()


def _validar_video(video: VideoColetado) -> None:
    campos_obrigatorios = {
        "titulo": video.titulo,
        "canal": video.canal,
        "plataforma": video.plataforma,
        "url": video.url,
    }
    faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor.strip()]
    if faltando:
        raise ValueError("Campos obrigatorios vazios: " + ", ".join(faltando))


def _normalizar_url(url: str) -> str:
    return url.strip().casefold()


def _video_para_linha(video: VideoColetado) -> dict[str, str | int]:
    return {
        "titulo": video.titulo,
        "canal": video.canal,
        "plataforma": video.plataforma,
        "url": video.url,
        "views": int(video.views),
        "likes": int(video.likes),
        "comentarios": int(video.comentarios),
        "data_publicacao": video.data_publicacao,
        "texto_comentarios": video.texto_comentarios,
    }
