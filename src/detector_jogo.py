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


# Padrao explicito na descricao: "Jogo: X", "Game: X" ou "Nome do jogo: X". O separador
# fica no grupo 1 de proposito: dois-pontos e um rotulo deliberado, hifen pode ser prosa
# comum ("Game - Play Store: baixe aqui"), e a deteccao trata os dois com pesos diferentes.
PADRAO_EXPLICITO = re.compile(
    r"^\s*(?:jogo|game|nome\s+do\s+jogo)\s*(:|-)\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Nome de jogo mais comprido que isto e quase certamente uma frase que caiu no padrao.
TAMANHO_MAXIMO_NOME_JOGO = 60


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

    for nome_explicito, rotulo_deliberado in _extrair_jogos_explicitos(descricao):
        jogo = _detectar_por_aliases(nome_explicito, jogos)
        if jogo is not None:
            return DeteccaoJogo(jogo, "alta", "descricao")
        # Nome fora do seed so e aceito como esta quando veio de um rotulo deliberado
        # ("Jogo: X"): ai e o autor declarando o jogo. Vindo de hifen, seguimos para as
        # outras fontes em vez de sequestrar a deteccao com um palpite fraco.
        if rotulo_deliberado:
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


# Procura marcadores explicitos ("Jogo: X", "Game - X") na descricao e devolve pares
# (nome limpo, rotulo_deliberado), sem exigir que o nome ja exista no seed.
# rotulo_deliberado e True so para o separador dois-pontos. Nomes implausiveis (link ou
# frase longa) sao descartados aqui: entrar como jogo poluiria o meus_videos.csv e o
# agrupamento do fit real com texto que nunca foi nome de jogo.
def _extrair_jogos_explicitos(descricao: str) -> list[tuple[str, bool]]:
    encontrados = []
    for correspondencia in PADRAO_EXPLICITO.finditer(descricao or ""):
        nome = _limpar_nome_extraido(correspondencia.group(2))
        if _nome_de_jogo_plausivel(nome):
            encontrados.append((nome, correspondencia.group(1) == ":"))
    return encontrados


# Filtro barato contra o que claramente nao e nome de jogo: vazio, link ou frase longa.
def _nome_de_jogo_plausivel(nome: str) -> bool:
    if not nome or len(nome) > TAMANHO_MAXIMO_NOME_JOGO:
        return False

    minusculo = nome.casefold()
    return "http" not in minusculo and "www." not in minusculo


# Jogo cujo termo MAIS LONGO aparece no texto. O criterio nao e a ordem do seed: casar um
# termo comprido e evidencia mais forte que casar um alias curto e generico, que aparece
# por coincidencia. Sem isso, "Mine Rescue no Roblox" virava Minecraft so porque o alias
# "mine" estava numa linha anterior do arquivo. Empate mantem a ordem do seed.
def _detectar_por_aliases(texto: str, jogos: list[JogoSeed]) -> JogoSeed | None:
    melhor_jogo = None
    melhor_tamanho = 0

    for jogo in jogos:
        for termo in _termos_do_jogo(jogo):
            if len(termo) > melhor_tamanho and _termo_aparece(texto, termo):
                melhor_jogo = jogo
                melhor_tamanho = len(termo)

    return melhor_jogo


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
