import re

from dataclasses import dataclass
from unicodedata import combining, normalize

from comentario_jogo import extrair_nome_do_comentario, normalizar_comentario
from modelos import ComentarioAnalisado, JogoSeed, VideoColetado


# Resultado da deteccao do jogo de um video, com a confianca e a fonte do sinal.
# confianca: alta | media | baixa | nao_detectado
# fonte: descricao | tags | comentario_dono | titulo | comentario_corroborado |
#        comentarios | nao_detectado
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
#
# Os espacos horizontais sao [ \t], nunca \s. O \s casa \n tambem, e o ^ e o $ com MULTILINE
# ancoram so as pontas do padrao — nao confinam o miolo dele. Em 42 videos do canal o autor
# deixou "Jogo : " em branco, e ali o \s* atravessava a linha vazia e capturava o banner
# seguinte, gravando "JOGOS COM DESCONTO NA NUUVEM" como nome do jogo, com confianca alta
# ainda por cima. Um rotulo vazio agora simplesmente nao casa, e a deteccao segue para as
# outras fontes — que nesses videos e justamente onde o nome de verdade esta: nos
# comentarios. O \r no fim cobre descricao com quebra de linha estilo Windows.
PADRAO_EXPLICITO = re.compile(
    r"^[ \t]*(?:jogo|game|nome[ \t]+do[ \t]+jogo)[ \t]*(:|-)[ \t]*(.+?)[ \t\r]*$",
    re.IGNORECASE | re.MULTILINE,
)

# Nome de jogo mais comprido que isto e quase certamente uma frase que caiu no padrao.
TAMANHO_MAXIMO_NOME_JOGO = 60

# Quantas PESSOAS diferentes precisam dizer o mesmo nome para um comentario de terceiro ser
# aceito. Um comentario solto nao basta: na amostra real, a resposta "Kid bengala 2" a uma
# pergunta de nome do jogo era troll, e o dono respondeu "one line" na mesma thread. Duas
# pessoas errarem igual, com a mesma grafia, e bem mais raro que uma brincar sozinha.
MINIMO_CORROBORACAO = 2

# A partir de quantas pessoas a corroboracao deixa de ser "baixa" e vira "media". Terceiro
# nunca chega a "alta" de proposito: "alta" fica reservada para a palavra do autor (descricao
# ou comentario do dono) e para a tag exata. Nao ha placar de terceiros que valha tanto
# quanto o dono do canal dizendo qual e o jogo.
CORROBORACAO_PARA_MEDIA = 3


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
# descricao explicita ("Jogo: X") > tags > comentario do dono > titulo >
# comentario corroborado > alias solto nos comentarios. Devolve o jogo, a confianca e a
# fonte. Sem nenhum sinal -> DeteccaoJogo(None, "nao_detectado", "nao_detectado").
#
# O comentario do dono entra ANTES do titulo porque e a palavra do autor sobre a propria
# obra — o mesmo peso que ja damos ao "Jogo: X" da descricao —, enquanto o titulo e so um
# alias que por acaso apareceu numa frase. Ja o comentario corroborado entra DEPOIS do
# titulo: e opiniao de publico, boa quando varias pessoas concordam, mas ainda derivada.
#
# comentarios_analisados e opcional: sem ele o comportamento e exatamente o de antes, o que
# mantem funcionando quem so tem os textos crus (main.py, coleta antiga, testes).
def detectar_jogo_em_conteudo(
    jogos: list[JogoSeed],
    titulo: str = "",
    descricao: str = "",
    tags: list[str] | None = None,
    comentarios: list[str] | None = None,
    comentarios_analisados: list[ComentarioAnalisado] | None = None,
) -> DeteccaoJogo:
    tags = tags or []
    comentarios = comentarios or []
    comentarios_analisados = comentarios_analisados or []

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

    deteccao = _detectar_por_comentario_do_dono(comentarios_analisados, jogos)
    if deteccao is not None:
        return deteccao

    jogo = _detectar_por_aliases(titulo, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, "media", "titulo")

    deteccao = _detectar_por_corroboracao(comentarios_analisados, jogos)
    if deteccao is not None:
        return deteccao

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


# O dono do canal dizendo o nome do jogo vale como declaracao do autor: uma unica ocorrencia
# ja basta, sem corroboracao. O cuidado nao esta em CONFIAR nele, esta em reconhecer QUANDO
# ele esta respondendo — na amostra real o dono tambem escreve muita conversa fiada
# ("braboo", "calado...", "eu msm") e um comentario fixo de divulgacao. Por isso o texto
# inteiro so vira nome quando a thread perguntou o nome do jogo; fora disso exige-se um
# formato declarado ("chama X", "o nome do jogo e X").
def _detectar_por_comentario_do_dono(
    comentarios: list[ComentarioAnalisado], jogos: list[JogoSeed]
) -> DeteccaoJogo | None:
    for comentario in comentarios:
        if not comentario.do_dono:
            continue
        nome = _nome_dito_no_comentario(comentario)
        if nome:
            return _deteccao_de_comentario(nome, jogos, "alta", "comentario_dono")
    return None


# Comentario de terceiro so entra quando PESSOAS DIFERENTES dizem o mesmo nome. Conta-se
# autor distinto, nao comentario: senao uma pessoa sozinha repetindo tres vezes viraria
# "corroboracao". Sem indice de autor (coleta antiga, autor_indice=-1) tudo colapsa em um
# unico autor e nada e aceito — falhar para o lado de nao detectar e o erro barato aqui.
def _detectar_por_corroboracao(
    comentarios: list[ComentarioAnalisado], jogos: list[JogoSeed]
) -> DeteccaoJogo | None:
    autores_por_nome: dict[str, set[int]] = {}
    original_por_nome: dict[str, str] = {}

    for comentario in comentarios:
        if comentario.do_dono:
            continue
        nome = _nome_dito_no_comentario(comentario)
        if not nome:
            continue
        chave = normalizar_comentario(nome)
        autores_por_nome.setdefault(chave, set()).add(comentario.autor_indice)
        original_por_nome.setdefault(chave, nome)

    if not autores_por_nome:
        return None

    chave = max(autores_por_nome, key=lambda item: len(autores_por_nome[item]))
    total_autores = len(autores_por_nome[chave])
    if total_autores < MINIMO_CORROBORACAO:
        return None

    confianca = "media" if total_autores >= CORROBORACAO_PARA_MEDIA else "baixa"
    return _deteccao_de_comentario(
        original_por_nome[chave], jogos, confianca, "comentario_corroborado"
    )


# Le o nome dito num comentario. A thread que perguntou o nome do jogo e o que autoriza a
# resposta seca ("lava and aqua"); fora dela, so um formato declarado conta.
def _nome_dito_no_comentario(comentario: ComentarioAnalisado) -> str:
    return extrair_nome_do_comentario(
        comentario.texto, aceitar_texto_inteiro=comentario.responde_pergunta_de_jogo
    )


# Casa o nome dito com o seed: quando bate, o nome canonico do seed vence (evita gravar
# "repo game" e "R.E.P.O." como dois jogos). Quando nao bate, o nome entra como esta com
# jogo_no_seed=False, do mesmo jeito que ja acontece no caminho da descricao — a linha vira
# "jogo_pendente_seed" e alguem decide depois se cadastra.
def _deteccao_de_comentario(
    nome: str, jogos: list[JogoSeed], confianca: str, fonte: str
) -> DeteccaoJogo:
    jogo = _detectar_por_aliases(nome, jogos)
    if jogo is not None:
        return DeteccaoJogo(jogo, confianca, fonte)

    return DeteccaoJogo(None, confianca, fonte, jogo_detectado=nome, jogo_no_seed=False)


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
