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


def test_em_conteudo_detecta_por_tag():
    deteccao = detectar_jogo_em_conteudo(
        _jogos_exemplo(),
        titulo="sem nome aqui",
        tags=["gameplay", "repo game", "terror"],
    )

    assert deteccao.jogo.nome == "R.E.P.O."
    assert deteccao.confianca == "media"
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


if __name__ == "__main__":
    unittest.main()
