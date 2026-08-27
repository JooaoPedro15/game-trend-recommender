import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from detector_jogo import detectar_jogo_em_conteudo, detectar_jogos_no_video
from modelos import JogoSeed, VideoColetado


class TestDetectorJogo(unittest.TestCase):
    def test_detecta_jogo_por_alias_nos_comentarios(self):
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

        self.assertEqual([j.nome for j in encontrados], ["R.E.P.O."])

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

def test_detecta_jogo_pelo_texto_dos_comentarios():
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

    assert resultado == [jogo]


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
