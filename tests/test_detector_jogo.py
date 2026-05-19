import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from detector_jogo import detectar_jogos_no_video
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


if __name__ == "__main__":
    unittest.main()
