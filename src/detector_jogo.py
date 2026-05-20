import re

from unicodedata import combining, normalize 
from modelos import JogoSeed, VideoColetado


def detectar_jogos_no_video(
    video: VideoColetado, jogos: list[JogoSeed]
) -> list[JogoSeed]:
    texto_busca = f"{video.titulo} {video.texto_comentarios}"
    encontrados = []

    for jogo in jogos:
        if any(_termo_aparece(texto_busca, termo) for termo in _termos_do_jogo(jogo)):
            encontrados.append(jogo)

    return encontrados


def _termos_do_jogo(jogo: JogoSeed) -> list[str]:
    termos = [jogo.nome, *jogo.aliases]
    termos_unicos = []
    vistos = set()

    for termo in termos:
        termo_limpo = termo.strip()
        chave = termo_limpo.casefold()
        if termo_limpo and chave not in vistos:
            termos_unicos.append(termo_limpo)
            vistos.add(chave)

    return termos_unicos


def _termo_aparece(texto: str, termo: str) -> bool:
    texto_normalizado = _normalizar_texto(texto)
    termo_normalizado = _normalizar_texto(termo)

    padrao = rf"(?<![A-Za-z0-9]){re.escape(termo_normalizado)}(?![A-Za-z0-9])"

    return re.search(padrao, texto_normalizado) is not None


def _normalizar_texto(texto: str) -> str:
    texto_sem_acento = "".join(
        caractere
        for caractere in normalize("NFKD", texto)
        if not combining(caractere)
    )

    return texto_sem_acento.casefold()
