import csv
from pathlib import Path

from modelos import CanalReferencia, JogoSeed, VideoColetado


def ler_canais_referencia(caminho: str | Path) -> list[CanalReferencia]:
    linhas = _ler_linhas(caminho)
    return [
        CanalReferencia(
            nome=linha.get("nome", "").strip(),
            plataforma=linha.get("plataforma", "").strip(),
            url=linha.get("url", "").strip(),
            peso=_para_float(linha.get("peso"), 1.0),
        )
        for linha in linhas
    ]


def ler_jogos_seed(caminho: str | Path) -> list[JogoSeed]:
    linhas = _ler_linhas(caminho)
    return [
        JogoSeed(
            nome=linha.get("nome", "").strip(),
            aliases=_separar_aliases(linha.get("aliases", "")),
            genero=linha.get("genero", "").strip(),
            fit_inicial=_para_float(linha.get("fit_inicial"), 0.0),
        )
        for linha in linhas
    ]


def ler_videos_coletados(caminho: str | Path) -> list[VideoColetado]:
    return [linha_para_video(linha) for linha in _ler_linhas(caminho)]


# Converte uma linha do CSV (dicionario) em um VideoColetado.
def linha_para_video(linha: dict[str, str]) -> VideoColetado:
    return VideoColetado(
        titulo=linha.get("titulo", "").strip(),
        canal=linha.get("canal", "").strip(),
        plataforma=linha.get("plataforma", "").strip(),
        url=linha.get("url", "").strip(),
        views=_para_int(linha.get("views"), 0),
        likes=_para_int(linha.get("likes"), 0),
        comentarios=_para_int(linha.get("comentarios"), 0),
        data_publicacao=linha.get("data_publicacao", "").strip(),
        texto_comentarios=linha.get("texto_comentarios", "").strip(),
    )


def _ler_linhas(caminho: str | Path) -> list[dict[str, str]]:
    caminho = Path(caminho)

    if not caminho.exists() or caminho.stat().st_size == 0:
        return []

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _separar_aliases(valor: str) -> list[str]:
    return [alias.strip() for alias in valor.split("|") if alias.strip()]


def _para_float(valor: str | None, padrao: float) -> float:
    if valor is None or not valor.strip():
        return padrao
    return float(valor)


def _para_int(valor: str | None, padrao: int) -> int:
    if valor is None or not valor.strip():
        return padrao
    return int(float(valor))
