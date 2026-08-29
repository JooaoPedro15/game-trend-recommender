# Heuristica de texto para achar o nome do jogo DENTRO de um comentario.
#
# Este modulo so responde duas perguntas sobre um texto solto:
#   1. esse comentario esta PERGUNTANDO o nome do jogo?
#   2. esse comentario esta RESPONDENDO com um nome, e qual?
# Quem decide o quanto confiar na resposta (dono do canal x terceiro corroborado) e o
# detector_jogo. A separacao existe porque sao decisoes de natureza diferente: aqui e
# leitura de texto, la e politica de confianca. Este modulo fica ABAIXO do detector_jogo na
# pilha de imports, por isso nao importa nada dele.
#
# As regras abaixo nao foram inventadas: sairam de uma amostra real de 18 videos do canal,
# lida via API. O formato real que motivou cada regra esta citado junto dela.

import re
from unicodedata import combining, normalize


# Nome mais comprido que isto e quase certamente uma frase inteira que caiu na regra. O
# limite de PALAVRAS e o que separa "lava and aqua" (resposta) de "lava and aqua meu nome
# nobre e de navegador" (resposta + recado colado).
TAMANHO_MAXIMO_NOME = 60
MAXIMO_PALAVRAS_NOME = 6

# Caracteres invisiveis que o YouTube injeta no comeco de respostas (zero-width space e
# amigos). Se nao forem removidos, quebram o strip e a comparacao de nomes iguais.
INVISIVEIS = "​‌‍﻿"

# Como o publico do canal escreve "jogo", incluindo os erros de digitacao que aparecem de
# verdade ("qual e o nome do jogp", "nome do jogi", "qual o nome do jg"). Sem tolerar esses
# erros, boa parte das perguntas reais nao seria reconhecida.
PADRAO_TERMO_JOGO = re.compile(
    r"(?<![a-z0-9])(?:jog[oaip]s?|jg|games?)(?![a-z0-9])",
    re.IGNORECASE,
)

# Uma pergunta pelo nome do jogo quase sempre COMECA com uma dessas palavras, mesmo quando
# nao tem ponto de interrogacao ("Nome do jogo", "Fala o nome do jogo para eu", "Que jogo e
# esse"). Exigir o inicio, em vez da mera presenca da palavra, e o que separa a pergunta do
# comentario que apenas fala sobre o jogo — e esse segundo tipo e a maioria esmagadora.
INICIOS_DE_PERGUNTA = (
    "qual", "quais", "quale", "cual", "cuau", "que ", "que?", "q ",
    "oq", "o que", "como", "onde", "nome", "alguem", "fala", "diz",
    "me diz", "poderia", "e qual", "cade", "manda",
)

# Respostas que aparecem dentro de uma thread de pergunta mas nao carregam nome nenhum.
# Sem esta lista, "ta na descricao" viraria um jogo chamado "ta na descricao".
RESPOSTAS_SEM_NOME = frozenset(
    {
        "sim", "nao", "n", "sei la", "nao sei", "n sei", "ja falei", "ja disse",
        "obrigado", "obg", "vlw", "valeu", "kkk", "kkkk", "eu msm", "eu mesmo",
        "braboo", "brabo", "opa", "amem", "f", "ta ai", "pronto", "descricao",
    }
)

# Comeco de resposta que aponta para outro lugar em vez de dizer o nome. Prefixo, e nao
# igualdade, porque o dono costuma emendar mais texto depois ("ta na descricao esse").
INICIOS_SEM_NOME = (
    "ta na descric", "esta na descric", "na descric", "link na descric",
    "ja ta na descric", "olha na descric", "ta escrito", "ta no video",
)

# Formatos em que alguem DECLARA o nome, em vez de so comentar sobre o jogo. Sao restritos
# de proposito: "o nome do jogo e X" e uma declaracao, mas "o jogo e X" pegaria qualquer
# opiniao ("o jogo e muito bom") e por isso ficou de fora. O dois-pontos entra pelo mesmo
# motivo que ja vale na descricao: e um rotulo deliberado, nao prosa.
PADROES_DECLARACAO = (
    re.compile(
        r"nome\s+(?:d[oe]\s+|desse\s+|deste\s+)?(?:jog[oaip]s?|jg|games?)"
        r"\s*(?:eh|[eé]|:|-)\s*(.+)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:se\s+)?chama(?:-se|\s+se)?\s+(.+)", re.IGNORECASE),
    re.compile(r"(?<![a-z0-9])(?:jog[oaip]|game)\s*:\s*(.+)", re.IGNORECASE),
)

# Mencao a outro usuario no comeco da resposta ("@fulano o nome do jogo e ..."). O handle e
# dado pessoal de terceiro: sai do texto antes de qualquer analise e nunca e propagado.
PADRAO_MENCAO = re.compile(rf"^[\s{INVISIVEIS}]*(?:@\S+[\s{INVISIVEIS}]*)+")

# Corta a frase no primeiro separador forte. Virgula e quebra de linha sao os que aparecem
# de verdade ("lava and aqua , nao ta na descricao esse"): o nome vem primeiro e o recado
# vem depois. O ponto final NAO entra aqui porque nome de jogo usa ponto ("R.E.P.O.").
PADRAO_CORTE = re.compile(r"\s*[,;\n\r|#]|\s{2,}|\s+-\s+")

# Pontuacao e enfeite que costumam grudar nas bordas do nome ("**one line**", "lava!").
BORDAS = " \t\"'`*_~()[]{}<>:;,.!?-" + INVISIVEIS


# Um comentario conta como pergunta pelo nome do jogo quando fala em "jogo" E tem forma de
# pergunta (interrogacao ou comeco interrogativo). As duas condicoes juntas sao o que evita
# confundir quem PERGUNTA o nome com quem apenas comenta o jogo.
def pergunta_nome_do_jogo(texto: str) -> bool:
    limpo = _sem_mencao(texto)
    if not PADRAO_TERMO_JOGO.search(limpo):
        return False
    if "?" in limpo:
        return True

    return normalizar_comentario(limpo).startswith(INICIOS_DE_PERGUNTA)


# Extrai o nome do jogo declarado num comentario; "" quando nao ha nome confiavel.
# aceitar_texto_inteiro liga o caso "resposta seca": dentro de uma thread que perguntou o
# nome, um comentario curto como "lava and aqua" ja E a resposta, sem rotulo nenhum. Fora
# desse contexto o texto inteiro nao vale nada, porque qualquer frase viraria nome de jogo.
def extrair_nome_do_comentario(texto: str, aceitar_texto_inteiro: bool = False) -> str:
    limpo = _sem_mencao(texto)
    if pergunta_nome_do_jogo(limpo):
        return ""

    for padrao in PADROES_DECLARACAO:
        correspondencia = padrao.search(limpo)
        if correspondencia:
            nome = _limpar_nome(correspondencia.group(1))
            if _nome_plausivel(nome):
                return nome

    if aceitar_texto_inteiro:
        nome = _limpar_nome(limpo)
        if _nome_plausivel(nome):
            return nome

    return ""


# Remove a mencao inicial para que ela nao entre no nome nem seja comparada como texto.
def _sem_mencao(texto: str) -> str:
    return PADRAO_MENCAO.sub("", texto or "").strip()


# Fica com o trecho antes do primeiro separador forte e tira pontuacao/enfeite das bordas.
def _limpar_nome(nome: str) -> str:
    pedaco = PADRAO_CORTE.split(nome or "", maxsplit=1)[0]
    return re.sub(r"\s+", " ", pedaco).strip().strip(BORDAS).strip()


# Filtro final contra o que claramente nao e nome de jogo. Cada condicao veio de um caso
# real da amostra: frase longa demais, resposta que aponta para a descricao, reacao curta
# ("braboo"), texto so de emoji e link.
def _nome_plausivel(nome: str) -> bool:
    if not nome or len(nome) > TAMANHO_MAXIMO_NOME:
        return False
    if len(nome.split()) > MAXIMO_PALAVRAS_NOME:
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", nome):
        return False

    normalizado = normalizar_comentario(nome)
    if normalizado in RESPOSTAS_SEM_NOME or normalizado.startswith(INICIOS_SEM_NOME):
        return False

    minusculo = nome.casefold()
    return "http" not in minusculo and "www." not in minusculo


# Normaliza para comparar: sem acento, espacos colapsados, sem pontuacao de borda, minusculo.
# E o mesmo texto usado para agrupar nomes iguais na corroboracao, entao "Lava and Aqua",
# "lava and aqua" e "lava and aqua!" contam como a mesma resposta.
def normalizar_comentario(texto: str) -> str:
    sem_acento = "".join(
        caractere
        for caractere in normalize("NFKD", texto or "")
        if not combining(caractere)
    )
    return re.sub(r"\s+", " ", sem_acento).strip(BORDAS).casefold()
