# Monta e filtra o ranking a partir dos CSVs. Extraido de main.py para ser reusado
# tanto pela CLI quanto pela API, sem nenhuma das duas depender da outra.

from datetime import date
from pathlib import Path

from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from meus_videos import ler_meus_videos
from modelos import VideoColetado
from ranker import calcular_ranking


def filtrar_por_plataforma(videos: list[VideoColetado], plataforma: str) -> list[VideoColetado]:
    plataforma_alvo = plataforma.casefold()
    return [video for video in videos if video.plataforma.casefold() == plataforma_alvo]


def filtrar_por_data(videos: list[VideoColetado], desde: date) -> list[VideoColetado]:
    selecionados = []
    for video in videos:
        try:
            data_video = date.fromisoformat(video.data_publicacao)
        except ValueError:
            continue
        if data_video >= desde:
            selecionados.append(video)
    return selecionados


# Aplica os filtros de plataforma e data e o limite Top N (se houver) e retorna o ranking.
# Os filtros incidem so nos videos de referencia; o fit real usa todo o historico do canal.
def montar_ranking(
    jogos,
    videos,
    canais,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
    meus_videos=None,
):
    if plataforma:
        videos = filtrar_por_plataforma(videos, plataforma)
    if desde is not None:
        videos = filtrar_por_data(videos, desde)
    ranking = calcular_ranking(jogos, videos, canais, meus_videos)
    if top is not None:
        ranking = ranking[:top]
    return ranking


# Le os CSVs do diretorio dado e monta o ranking. data_dir aponta para a pasta com
# jogos_seed.csv e canais_referencia.csv; videos_csv e meus_videos_csv sao caminhos
# explicitos porque a CLI e a API podem apontar para arquivos com nomes diferentes.
def carregar_ranking(
    data_dir: str | Path,
    videos_csv: str | Path,
    meus_videos_csv: str | Path,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
):
    data_dir = Path(data_dir)
    canais = ler_canais_referencia(data_dir / "canais_referencia.csv")
    jogos = ler_jogos_seed(data_dir / "jogos_seed.csv")
    videos = ler_videos_coletados(videos_csv)
    meus_videos = ler_meus_videos(meus_videos_csv)
    return montar_ranking(jogos, videos, canais, plataforma, top, desde, meus_videos)
