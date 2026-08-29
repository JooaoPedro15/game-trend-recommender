import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from detector_jogo import detectar_jogo_em_conteudo, detectar_jogos_no_video
from modelos import ComentarioAnalisado, JogoSeed, VideoColetado


class TestDetectorJogo(unittest.TestCase):
    # Antes, um alias solto nos comentarios bastava para detectar o jogo. Amostra real de
    # canais de referencia mostrou comentario como sinal fraco (curiosidade, nao
    # identificacao) e fonte de falso positivo; a deteccao passou a ler so titulo, descricao
    # e tags. Aqui o nome so aparece no comentario, entao nao deve mais ser encontrado.
    def test_jogo_citado_so_nos_comentarios_nao_e_detectado(self):
        jogo = JogoSeed(
            nome="R.E.P.O.",
            aliases=["repo", "r.e.p.o", "repo game"],
            genero="horror engracado",
            fit_inicial=9,
        )
        video = VideoColetado(
            titulo="Esse jogo de terror me quebrou",
            canal="Canal Referencia 1",
            plataforma="youtube",
            url="https://exemplo.com/video1",
            views=800000,
            likes=90000,
            comentarios=1200,
            data_publicacao="2026-05-15",
            texto_comentarios="qual nome do jogo? REPO muito bom",
        )

        encontrados = detectar_jogos_no_video(video, [jogo])

        self.assertEqual(encontrados, [])

    def test_detecta_jogo_pelo_nome_principal_no_titulo(self):
        jogo = JogoSeed(
            nome="Content Warning",
            aliases=["content warning"],
            genero="horror coop",
            fit_inicial=10,
        )
        video = VideoColetado(
            titulo="CONTENT WARNING deu muito errado",
            canal="Canal Referencia 2",
            plataforma="tiktok",
            url="https://exemplo.com/video2",
            views=150000,
            likes=12000,
            comentarios=300,
            data_publicacao="2026-05-16",
            texto_comentarios="",
        )

        encontrados = detectar_jogos_no_video(video, [jogo])

        self.assertEqual([j.nome for j in encontrados], ["Content Warning"])

# Mesma mudanca de contrato do teste acima: comentario deixou de ser fonte da deteccao
# de video de referencia. O nome so aparece na pergunta do comentario, entao o jogo nao
# deve mais ser encontrado.
def test_jogo_citado_so_na_pergunta_do_comentario_nao_e_detectado():
    jogo = JogoSeed(
        nome="Schedule I",
        aliases=["schedule 1", "schedule one"],
        genero="simulador",
        fit_inicial=9.0,
    )

    video = VideoColetado(
        titulo="Esse jogo viralizou do nada",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/teste",
        views=100000,
        likes=10000,
        comentarios=500,
        data_publicacao="2026-05-20",
        texto_comentarios="qual o nome do jogo? schedule 1?",
    )

    resultado = detectar_jogos_no_video(video, [jogo])

    assert resultado == []


def _jogos_exemplo():
    return [
        JogoSeed(nome="Schedule I", aliases=["schedule 1", "schedule one"], genero="sim", fit_inicial=9.0),
        JogoSeed(nome="R.E.P.O.", aliases=["repo", "repo game"], genero="horror", fit_inicial=9.0),
    ]


def test_em_conteudo_descricao_explicita_tem_confianca_alta():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="gameplay aleatorio",
        descricao="Inscreva-se!\nJogo: Schedule I\nObrigado",
    )

    assert deteccao.jogo.nome == "Schedule I"
    assert deteccao.confianca == "alta"
    assert deteccao.fonte == "descricao"


def test_em_conteudo_descricao_explicita_com_hifen_detecta():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem pista",
        descricao="Game - R.E.P.O.",
    )

    assert deteccao.jogo.nome == "R.E.P.O."
    assert deteccao.confianca == "alta"
    assert deteccao.fonte == "descricao"


def test_em_conteudo_descricao_explicita_fora_do_seed_nao_descarta():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem pista",
        descricao="Jogo: Dark Hours",
    )

    assert deteccao.jogo is None
    assert deteccao.jogo_detectado == "Dark Hours"
    assert deteccao.confianca == "alta"
    assert deteccao.fonte == "descricao"
    assert deteccao.jogo_no_seed is False


def test_em_conteudo_detecta_por_tag():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem nome aqui",
        tags=["gameplay", "repo game", "terror"],
    )

    assert deteccao.jogo.nome == "R.E.P.O."
    assert deteccao.confianca == "alta"
    assert deteccao.fonte == "tags"


def test_em_conteudo_detecta_pelo_titulo():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="SCHEDULE 1 me viciou",
    )

    assert deteccao.jogo.nome == "Schedule I"
    assert deteccao.confianca == "media"
    assert deteccao.fonte == "titulo"


def test_em_conteudo_detecta_por_comentario_com_confianca_baixa():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="que jogo e esse??",
        comentarios=["nao sei", "acho que e repo", "muito bom"],
    )

    assert deteccao.jogo.nome == "R.E.P.O."
    assert deteccao.confianca == "baixa"
    assert deteccao.fonte == "comentarios"


def test_em_conteudo_nenhum_jogo_detectado():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        descricao="sem nada relevante",
        tags=["vlog"],
        comentarios=["legal"],
    )

    assert deteccao.jogo is None
    assert deteccao.confianca == "nao_detectado"
    assert deteccao.fonte == "nao_detectado"
    assert deteccao.motivo_nao_detectado


if __name__ == "__main__":
    unittest.main()


# --- Desempate entre jogos: termo mais longo vence, nao a ordem do arquivo ---
#
# _detectar_por_aliases devolvia o primeiro jogo que casasse, percorrendo o seed na ordem
# das linhas. Com isso um alias curto e generico ("mine") roubava a deteccao de um jogo
# citado por inteiro so por estar antes no arquivo. Casar um termo longo e evidencia mais
# forte: mais caracteres, menos chance de coincidencia.

def _seed_com_alias_curto():
    return [
        JogoSeed(nome="Minecraft", aliases=["minecraft", "mine"], genero="sandbox", fit_inicial=7),
        JogoSeed(nome="Roblox", aliases=["roblox"], genero="variado", fit_inicial=7),
    ]


def test_termo_mais_longo_vence_alias_curto():
    deteccao = detectar_jogo_em_conteudo(_seed_com_alias_curto(), titulo="Mine Rescue no Roblox")

    assert deteccao.jogo.nome == "Roblox"


def test_desempate_nao_depende_da_ordem_do_seed():
    invertido = list(reversed(_seed_com_alias_curto()))

    deteccao = detectar_jogo_em_conteudo(invertido, titulo="Mine Rescue no Roblox")

    assert deteccao.jogo.nome == "Roblox"


def test_alias_curto_ainda_detecta_quando_e_o_unico_sinal():
    deteccao = detectar_jogo_em_conteudo(_seed_com_alias_curto(), titulo="joguei mine ontem")

    assert deteccao.jogo.nome == "Minecraft"


# --- Confianca proporcional a deliberacao do marcador ---
#
# "Jogo: X" e um rotulo explicito e vale mesmo para jogo fora do seed. "Game - X" pode ser
# prosa comum numa descricao ("Game - Play Store: baixe aqui"), entao so conta quando o
# nome casa com o seed. Sem essa distincao, uma linha qualquer com hifen sequestrava a
# deteccao com confianca alta e bloqueava titulo, tags e comentarios.

def test_marcador_com_hifen_fora_do_seed_nao_bloqueia_as_outras_fontes():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="Roblox gameplay",
        descricao="Game - Play Store: baixe aqui",
    )

    assert deteccao.jogo.nome == "Roblox"
    assert deteccao.fonte == "titulo"


def test_marcador_com_hifen_fora_do_seed_sem_outra_fonte_nao_detecta():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="sem pista",
        descricao="Game - Play Store: baixe aqui",
    )

    assert deteccao.detectou is False
    assert deteccao.jogo_detectado == ""


def test_marcador_com_dois_pontos_fora_do_seed_continua_valendo():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="Roblox gameplay",
        descricao="Jogo: Lava and Aqua",
    )

    assert deteccao.jogo_detectado == "Lava and Aqua"
    assert deteccao.jogo_no_seed is False
    assert deteccao.fonte == "descricao"


def test_marcador_com_link_e_descartado():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="Roblox gameplay",
        descricao="Jogo: https://loja.com/jogo",
    )

    assert deteccao.jogo.nome == "Roblox"


def test_marcador_com_frase_longa_demais_e_descartado():
    frase = "compre agora com desconto na promocao de fim de ano da loja parceira oficial"

    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="Roblox gameplay",
        descricao=f"Jogo: {frase}",
    )

    assert deteccao.jogo.nome == "Roblox"


# --- Marcador vazio nao pode engolir o paragrafo seguinte ---
#
# Achado no dado real: 42 videos (18,2M views) foram detectados como o jogo
# "JOGOS COM DESCONTO NA NUUVEM", a linha de afiliado da descricao. A causa e que \s
# inclui \n: com "jogo : " sem valor, o \s* depois do separador atravessava as linhas em
# branco e capturava o proximo paragrafo. ^ e $ com MULTILINE ancoram as pontas, mas nao
# confinam o que esta entre elas.

_DESCRICAO_MARCADOR_VAZIO = (
    "Obrigado por assistir :) \n"
    "\n"
    "jogo : \n"
    "\n"
    "JOGOS COM DESCONTO NA NUUVEM\n"
    "https://click.linksynergy.com/deeplink?id=abc\n"
)


def test_marcador_vazio_nao_engole_o_paragrafo_seguinte():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(), titulo="sem pista", descricao=_DESCRICAO_MARCADOR_VAZIO
    )

    assert deteccao.detectou is False
    assert deteccao.jogo_detectado == ""


def test_marcador_vazio_nao_bloqueia_a_deteccao_pelo_titulo():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="Roblox gameplay",
        descricao=_DESCRICAO_MARCADOR_VAZIO,
    )

    assert deteccao.jogo.nome == "Roblox"


def test_marcador_preenchido_continua_detectando():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="sem pista",
        descricao="Obrigado por assistir :)\n\njogo : Roblox\n\noutra coisa qualquer\n",
    )

    assert deteccao.jogo.nome == "Roblox"
    assert deteccao.fonte == "descricao"


def test_marcador_com_espacos_ao_redor_continua_detectando():
    deteccao = detectar_jogo_em_conteudo(
        _seed_com_alias_curto(),
        titulo="sem pista",
        descricao="  Jogo :   Roblox   \nmais texto\n",
    )

    assert deteccao.jogo.nome == "Roblox"
# ---------------------------------------------------------------------------
# Deteccao pelo comentario: palavra do dono x corroboracao de terceiros.
# Os textos abaixo sao formatos reais do canal (amostra de 18 videos lida via API).
# ---------------------------------------------------------------------------


def _comentario(texto, dono=False, pergunta=False, autor=0):
    return ComentarioAnalisado(
        texto=texto, do_dono=dono, responde_pergunta_de_jogo=pergunta, autor_indice=autor
    )


def test_comentario_do_dono_respondendo_pergunta_tem_confianca_alta():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="Eu tenho que salvar esse homem....",
        comentarios_analisados=[
            _comentario("Nome do game?", autor=1),
            _comentario("lava and aqua", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo_detectado == "lava and aqua"
    assert deteccao.confianca == "alta"
    assert deteccao.fonte == "comentario_dono"
    assert deteccao.jogo_no_seed is False


# O dono nem sempre responde so o nome: "lava and aqua tem no google" e resposta real. O
# recado colado fica no nome enquanto o jogo e desconhecido (a linha nasce como
# jogo_pendente_seed, para revisao humana), mas assim que o jogo entra no seed o alias e
# encontrado DENTRO da frase e o nome canonico volta a valer. E o que impede o ruido de
# virar um jogo separado no agrupamento do fit real.
def test_recado_colado_no_nome_some_quando_o_jogo_entra_no_seed():
    jogos = [JogoSeed(nome="Lava and Aqua", aliases=["lava and aqua"], genero="puzzle", fit_inicial=7.0)]

    deteccao = detectar_jogo_em_conteudo(
        jogos,
        titulo="Tentando fugir da lava....",
        comentarios_analisados=[
            _comentario("Qual o nome do jogo?", autor=1),
            _comentario("lava and aqua tem no google", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo.nome == "Lava and Aqua"
    assert deteccao.jogo_no_seed is True
    assert deteccao.fonte == "comentario_dono"


def test_comentario_do_dono_que_casa_com_o_seed_usa_o_nome_canonico():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem pista",
        comentarios_analisados=[
            _comentario("qual o nome do jogo?", autor=1),
            _comentario("chama repo game", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo.nome == "R.E.P.O."
    assert deteccao.jogo_no_seed is True
    assert deteccao.fonte == "comentario_dono"


# O dono conversa muito nos comentarios sem responder nada. Confiar nele nao pode virar
# "todo comentario dele e nome de jogo".
def test_conversa_do_dono_nao_vira_nome_de_jogo():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("Primeiro", autor=1),
            _comentario("brabooo", dono=True, pergunta=False),
            _comentario("calado…", dono=True, pergunta=False),
        ],
    )

    assert deteccao.confianca == "nao_detectado"


# O comentario fixo de divulgacao e do dono e fica no topo, nunca dentro de uma thread de
# pergunta; nao pode ser lido como declaracao de jogo.
def test_comentario_fixo_de_divulgacao_do_dono_e_ignorado():
    fixo = "Obrigado por assistir\nSEGUE AI\nInsta : https://www.instagram.com/jootta15"

    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[_comentario(fixo, dono=True, pergunta=False)],
    )

    assert deteccao.confianca == "nao_detectado"


def test_comentario_do_dono_vence_o_titulo():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="SCHEDULE 1 me viciou",
        comentarios_analisados=[
            _comentario("Qual o nome do jogo?", autor=1),
            _comentario("chama one line", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo_detectado == "one line"
    assert deteccao.fonte == "comentario_dono"


def test_descricao_explicita_ainda_vence_o_comentario_do_dono():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem pista",
        descricao="Jogo: Schedule I",
        comentarios_analisados=[_comentario("one line", dono=True, pergunta=True)],
    )

    assert deteccao.jogo.nome == "Schedule I"
    assert deteccao.fonte == "descricao"


# Um terceiro sozinho pode estar brincando: na amostra real, a resposta a "Qual nome do
# jogo?" foi "Kid bengala 2" e o dono respondeu "one line" na mesma thread.
def test_um_unico_terceiro_nao_basta():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("Qual nome do jogo?", autor=1),
            _comentario("Kid bengala 2", pergunta=True, autor=2),
        ],
    )

    assert deteccao.confianca == "nao_detectado"


def test_dois_terceiros_independentes_corroboram_com_confianca_baixa():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("Qual nome do jogo?", autor=1),
            _comentario("lava and aqua", pergunta=True, autor=2),
            _comentario("o nome do jogo é lava and aqua", autor=3),
        ],
    )

    assert deteccao.jogo_detectado == "lava and aqua"
    assert deteccao.confianca == "baixa"
    assert deteccao.fonte == "comentario_corroborado"
    assert deteccao.jogo_no_seed is False


def test_tres_terceiros_independentes_sobem_a_confianca_para_media():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("Lava and Aqua", pergunta=True, autor=1),
            _comentario("lava and aqua!", pergunta=True, autor=2),
            _comentario("chama lava and aqua", autor=3),
        ],
    )

    assert deteccao.jogo_detectado == "Lava and Aqua"
    assert deteccao.confianca == "media"
    assert deteccao.fonte == "comentario_corroborado"


# Corroboracao conta PESSOAS, nao comentarios: senao bastaria uma pessoa insistir.
def test_mesma_pessoa_repetindo_nao_corrobora():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("lava and aqua", pergunta=True, autor=7),
            _comentario("lava and aqua", pergunta=True, autor=7),
            _comentario("chama lava and aqua", autor=7),
        ],
    )

    assert deteccao.confianca == "nao_detectado"


# Sem indice de autor (coleta antiga) nao da para saber se sao pessoas diferentes; o certo
# e nao aceitar.
def test_sem_indice_de_autor_nao_ha_corroboracao():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("lava and aqua", pergunta=True, autor=-1),
            _comentario("chama lava and aqua", autor=-1),
        ],
    )

    assert deteccao.confianca == "nao_detectado"


def test_dono_vence_corroboracao_de_terceiros():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="dia comum",
        comentarios_analisados=[
            _comentario("Qual nome do jogo?", autor=1),
            _comentario("Kid bengala 2", pergunta=True, autor=2),
            _comentario("chama Kid bengala 2", autor=3),
            _comentario("one line", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo_detectado == "one line"
    assert deteccao.fonte == "comentario_dono"


# Regressao: o rotulo "Jogo :" vazio (dezenas de videos do canal) roubava a linha seguinte
# da descricao e gravava o banner de patrocinio como nome do jogo, com confianca alta.
def test_rotulo_de_jogo_vazio_nao_rouba_a_linha_seguinte():
    descricao = (
        "Obrigado por assistir :)\n\nJogo : \n\nJOGOS COM DESCONTO NA NUUVEM\nhttps://loja.com"
    )

    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem pista",
        descricao=descricao,
    )

    assert deteccao.confianca == "nao_detectado"


# Com o rotulo vazio fora do caminho, o nome real (que esta nos comentarios) aparece.
def test_rotulo_vazio_deixa_o_comentario_do_dono_detectar():
    descricao = "Obrigado por assistir :)\n\nJogo : \n\nJOGOS COM DESCONTO NA NUUVEM"

    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="Eu tenho que fugir da lava",
        descricao=descricao,
        comentarios_analisados=[
            _comentario("Nome do jogo?", autor=1),
            _comentario("lava and aqua", dono=True, pergunta=True),
        ],
    )

    assert deteccao.jogo_detectado == "lava and aqua"
    assert deteccao.fonte == "comentario_dono"


# --- Deteccao de video de referencia usa so texto do autor ---
#
# Amostra real de dois canais de referencia: 400 comentarios, 5 perguntas pelo nome do
# jogo, ZERO respostas. Comentario ali carrega curiosidade, nao identificacao. E incluir
# comentario liga um falso positivo conhecido: um alias solto em 100 comentarios de um
# video sobre "a evolucao das logos do facebook e do youtube" resolvia como Roblox.

def _video_referencia(titulo="", descricao="", tags=None, comentarios=""):
    video = VideoColetado(
        titulo=titulo,
        canal="Lozao",
        plataforma="youtube",
        url="https://y/1",
        views=1000,
        likes=10,
        comentarios=5,
        data_publicacao="2026-08-01",
        texto_comentarios=comentarios,
    )
    video.descricao = descricao
    video.tags = tags or []
    return video


def test_detecta_jogo_citado_na_descricao():
    achados = detectar_jogos_no_video(
        _video_referencia(titulo="MEU BARCO NAUFRAGO", descricao="nesse video eu trouxe Roblox"),
        _seed_com_alias_curto(),
    )

    assert [j.nome for j in achados] == ["Roblox"]


def test_detecta_jogo_citado_nas_tags():
    achados = detectar_jogos_no_video(
        _video_referencia(titulo="sem pista", tags=["gameplay", "roblox"]),
        _seed_com_alias_curto(),
    )

    assert [j.nome for j in achados] == ["Roblox"]


def test_alias_solto_em_comentario_nao_detecta_mais():
    achados = detectar_jogos_no_video(
        _video_referencia(
            titulo="A evolucao das logos do facebook e do youtube",
            comentarios="alguem ai joga roblox? eu jogo minecraft todo dia",
        ),
        _seed_com_alias_curto(),
    )

    assert achados == []


def test_texto_comentarios_continua_no_modelo():
    # A descoberta depende desse campo; so a deteccao parou de le-lo. Remover o campo
    # quebraria o score_descoberta, que e o proximo passo do plano.
    video = _video_referencia(comentarios="qual o nome do jogo")

    assert video.texto_comentarios == "qual o nome do jogo"
