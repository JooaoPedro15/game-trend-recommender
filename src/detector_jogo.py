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
    jogo_detectado: str = ""
    motivo_nao_detectado: str = ""
    jogo_no_seed: bool = True

    # Preenche a string salva quando o jogo veio de um registro do seed.
    def __post_init__(self) -> None:
        if self.jogo is not None and not self.jogo_detectado:
            self.jogo_detectado = self.jogo.nome

    # Indica se houve um nome detectado, mesmo quando ele ainda nao existe no seed.
    @property
    def detectou(self) -> bool:
        return bool(self.jogo_detectado.strip())


# Padrao explicito na descricao: "Jogo: X", "Game: X" ou "Nome do jogo: X".
PADRAO_EXPLICITO = re.compile(
    r"^\s*(?:jogo|game|nome\s+do\s+jogo)\s*(?::|-)\s*(.+?)\s*$",
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

    for nome_explicito in _extrair_jogos_explicitos(descricao):
        jogo = _detectar_por_aliases(nome_explicito, jogos)
        if jogo is not None:
            return DeteccaoJogo(jogo, "alta", "descricao")
        return DeteccaoJogo(
            None,
            "alta",
            "descricao",
            jogo_detectado=nome_explicito,
            jogo_no_seed=False,
        )

    jogo = _detectar_por_tag_exata(tags, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "alta", "tags")

    jogo = _detectar_por_aliases(titulo, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "media", "titulo")

    jogo = _detectar_por_aliases(" ".join(comentarios), jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "baixa", "comentarios")

    motivo = _motivo_nao_detectado(titulo, descricao, tags, comentarios)
    return DeteccaoJogo(
        None,
        "nao_detectado",
        "nao_detectado",
        motivo_nao_detectado=motivo,
    )


# Procura marcadores explicitos ("Jogo: X", "Game - X") na descricao e devolve os
# nomes limpos, sem exigir que eles ja existam no seed.
def _extrair_jogos_explicitos(descricao: str) -> list[str]:
    nomes = []
    for correspondencia in PADRAO_EXPLICITO.finditer(descricao or ""):
        nome = _limpar_nome_extraido(correspondencia.group(1))
        if nome:
            nomes.append(nome)
    return nomes


# Primeiro jogo cujo nome/alias aparece no texto (mesma logica de _termo_aparece).
def _detectar_por_aliases(texto: str, jogos: list[JogoSeed]) -> JogoSeed | None:
    for jogo in jogos:
        if any(_termo_aparece(texto, termo) for termo in _termos_do_jogo(jogo)):
            return jogo
    return None


# Primeiro jogo cujo nome/alias casa exatamente com uma tag normalizada.
def _detectar_por_tag_exata(tags: list[str], jogos: list[JogoSeed]) -> JogoSeed | None:
    tags_normalizadas = {_normalizar_texto(tag) for tag in tags if tag.strip()}
    for jogo in jogos:
        if any(_normalizar_texto(termo) in tags_normalizadas for termo in _termos_do_jogo(jogo)):
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

    return re.sub(r"\s+", " ", texto_sem_acento).strip().casefold()


def _limpar_nome_extraido(nome: str) -> str:
    nome = re.split(r"\s+#|\s+\||\s{2,}", nome or "", maxsplit=1)[0]
    return re.sub(r"\s+", " ", nome.strip(" \t-:;,")).strip()


def _motivo_nao_detectado(
    titulo: str,
    descricao: str,
    tags: list[str],
    comentarios: list[str],
) -> str:
    if not any([titulo.strip(), descricao.strip(), tags, comentarios]):
        return "sem_texto_para_detectar"
    return "nenhum_jogo_do_seed_encontrado_nas_fontes"
