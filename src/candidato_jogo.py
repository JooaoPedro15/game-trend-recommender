# Extrai NOME CANDIDATO de jogo do texto de um video de referencia, para o caso em que
# nenhum jogo do seed foi identificado. Candidato nunca entra no seed sozinho: ele aparece
# numa lista que uma pessoa le e decide. Por isso o filtro aqui pode ser tolerante — ruido
# numa lista custa um segundo de leitura, ruido no seed contamina ranking e fit_real.
#
# Os templates saem de amostragem real (2026-08-29, @lozao e @ElCamacho24). Canal novo que
# escreva de outro jeito nao e coberto ate alguem observar o padrao dele.

import re


# Templates de apresentacao observados. O grupo 1 e o nome candidato. A ordem importa: o
# mais especifico vem primeiro, senao o generico casa antes e engole o marcador.
TEMPLATES = [
    re.compile(
        r"(?:nesse|neste)\s+v[ií]deo\s+eu\s+trouxe\s+(?:um\s+)?(?:jogo|game)\s+chamado\s+(.+)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:um|uma)\s+(?:jogo|game)\s+chamado\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:nesse|neste)\s+v[ií]deo\s+eu\s+trouxe\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:en\s+este|neste)\s+v[ií]deo\s+jugamos\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:el\s+d[ií]a\s+de\s+)?hoy\s+jugamos\s+(.+)", re.IGNORECASE),
    re.compile(r"volvimos\s+a\s+jugar\s+(.+)", re.IGNORECASE),
    re.compile(r"continuamos\s+con\s+la\s+serie\s+de\s+(.+)", re.IGNORECASE),
    re.compile(r"terminamos\s+(.+)", re.IGNORECASE),
]

# Hashtag do titulo. O ElCamacho24 marca o jogo assim nos shorts, onde a descricao e vazia.
PADRAO_HASHTAG = re.compile(r"#(\w{3,30})")

# Hashtag que nunca e nome de jogo. Todas apareceram na amostra e so gerariam ruido.
HASHTAG_IGNORADA = {
    "shorts", "short", "clips", "clip", "gameplay", "games", "game",
    "viral", "fyp", "gaming", "funny", "meme", "memes",
}

# Um nome de jogo tem poucas palavras. Acima disso a captura pegou a frase inteira. 7 e
# nao 5 porque o template generico "trouxe (.+)" (sem "chamado") as vezes carrega junto um
# qualificador antes do corte por virgula/conectivo — "How to fish um game de pescaria" tem
# 7 palavras e ainda e um nome plausivel; a frase-lixo de teste tem 16 e continua rejeitada.
MAXIMO_PALAVRAS = 7
TAMANHO_MAXIMO = 60

# Corta o candidato no primeiro separador forte. O ponto NAO entra: nome como "R.E.P.O."
# depende dele. Os conectivos entram porque a prosa real cola recado no nome sem virgula
# ("hoy jugamos Hello Neighbor con el mod de fredbear") — sem cortar ali a captura estoura
# o limite de palavras e o nome inteiro se perde.
PADRAO_CORTE = re.compile(r"[,\n|]|\s+(?:con|com|pero|mas|but)\s+", re.IGNORECASE)


# Nomes candidatos encontrados no texto do autor, sem repetir e preservando a ordem em que
# aparecem. Lista vazia quando nada plausivel foi achado — que e o caso mais comum nos
# shorts, onde a descricao e vazia e o titulo nao tem hashtag util.
def candidatos_do_video(titulo: str, descricao: str) -> list[str]:
    achados: list[str] = []

    for linha in (descricao or "").splitlines():
        for template in TEMPLATES:
            correspondencia = template.search(linha)
            if correspondencia is None:
                continue
            nome = _limpar(correspondencia.group(1))
            if _plausivel(nome):
                _acrescentar(achados, nome)
            break

    for hashtag in PADRAO_HASHTAG.findall(titulo or ""):
        if hashtag.casefold() not in HASHTAG_IGNORADA:
            _acrescentar(achados, hashtag)

    return achados


# Acrescenta sem repetir, ignorando caixa: a mesma coisa escrita de dois jeitos na prosa e
# na hashtag e um candidato so para quem le a lista.
def _acrescentar(achados: list[str], nome: str) -> None:
    if nome.casefold() not in {existente.casefold() for existente in achados}:
        achados.append(nome)


def _limpar(nome: str) -> str:
    pedaco = PADRAO_CORTE.split(nome or "", maxsplit=1)[0]
    pedaco = re.sub(r"\s+", " ", pedaco).strip().strip(" .:-—!?").strip()
    # Tira emoji e outros simbolos presos nas bordas (ex.: "Shieldwall 🗣️"). strip() nao
    # remove emoji porque eles nao sao whitespace nem estao no conjunto de corte acima.
    pedaco = re.sub(r"^[^\w]+|[^\w]+$", "", pedaco, flags=re.UNICODE)
    return pedaco.strip()


# Filtro contra o que claramente nao e nome de jogo. Cada condicao veio de um caso real da
# amostra: frase inteira capturada por template generico, e link solto na prosa.
def _plausivel(nome: str) -> bool:
    if not nome or len(nome) > TAMANHO_MAXIMO:
        return False
    if len(nome.split()) > MAXIMO_PALAVRAS:
        return False
    minusculo = nome.casefold()
    if "http" in minusculo or "www." in minusculo:
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", nome))
