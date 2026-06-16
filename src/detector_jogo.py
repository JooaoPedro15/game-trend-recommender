import re

from dataclasses import dataclass
from unicodedata import combining, normalize
from modelos import JogoSeed, VideoColetado


# Resultado da deteccao do jogo de um video, com a confianca e a fonte do sinal.
# confianca: alta | media | baixa | nao_detectado
# fonte: descricao | tags | titulo | comentarios | nao_detectado
@dataclass
class DeteccaoJogo:
    jogo: JogoSeed | None
    confianca: str
    fonte: str


# Padrao explicito na descricao: "Jogo: X", "Game: X" ou "Nome do jogo: X".
PADRAO_EXPLICITO = re.compile(
    r"^\s*(?:jogo|game|nome do jogo)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def detectar_jogos_no_video(
    video: VideoColetado, jogos: list[JogoSeed]
) -> list[JogoSeed]:
    texto_busca = f"{video.titulo} {video.texto_comentarios}"
    encontrados = []

    for jogo in jogos:
        if any(_termo_aparece(texto_busca, termo) for termo in _termos_do_jogo(jogo)):
            encontrados.append(jogo)

    return encontrados


# Detecta o jogo de um video combinando varias fontes, em ordem de confianca:
# descricao explicita ("Jogo: X") > tags > titulo > comentarios. Devolve o jogo, a
# confianca e a fonte. Sem nenhum sinal -> DeteccaoJogo(None, "nao_detectado", "nao_detectado").
def detectar_jogo_em_conteudo(
    jogos: list[JogoSeed],
    titulo: str = "",
    descricao: str = "",
    tags: list[str] | None = None,
    comentarios: list[str] | None = None,
) -> DeteccaoJogo:
    tags = tags or []
    comentarios = comentarios or []

    jogo = _detectar_explicito_na_descricao(descricao, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "alta", "descricao")

    jogo = _detectar_por_aliases(" ".join(tags), jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "media", "tags")

    jogo = _detectar_por_aliases(titulo, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "media", "titulo")

    jogo = _detectar_por_aliases(" ".join(comentarios), jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "baixa", "comentarios")

    return DeteccaoJogo(None, "nao_detectado", "nao_detectado")


# Procura "Jogo:/Game:/Nome do jogo: <nome>" na descricao e casa o nome citado com um
# jogo do seed. Retorna o primeiro jogo casado, ou None se nada bater.
def _detectar_explicito_na_descricao(
    descricao: str, jogos: list[JogoSeed]
) -> JogoSeed | None:
    for correspondencia in PADRAO_EXPLICITO.finditer(descricao or ""):
        jogo = _detectar_por_aliases(correspondencia.group(1), jogos)
        if jogo is not None:
            return jogo
    return None


# Primeiro jogo cujo nome/alias aparece no texto (mesma logica de _termo_aparece).
def _detectar_por_aliases(texto: str, jogos: list[JogoSeed]) -> JogoSeed | None:
    for jogo in jogos:
        if any(_termo_aparece(texto, termo) for termo in _termos_do_jogo(jogo)):
            return jogo
    return None


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
