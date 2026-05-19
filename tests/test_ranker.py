import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, VideoColetado
from ranker import calcular_ranking
from main import imprimir_ranking


class TestRanker(unittest.TestCase):
    def test_ordena_jogo_com_maior_potencial_no_topo(self):
        canais = [
            CanalReferencia(
                nome="Canal Referencia 1",
                plataforma="youtube",
                url="https://youtube.com/@canal1",
                peso=1.0,
            ),
            CanalReferencia(
                nome="Canal Referencia 2",
                plataforma="tiktok",
                url="https://tiktok.com/@canal2",
                peso=1.2,
            ),
        ]
        jogos = [
            JogoSeed(
                nome="R.E.P.O.",
                aliases=["repo", "r.e.p.o", "repo game"],
                genero="horror engracado",
                fit_inicial=9,
            ),
            JogoSeed(
                nome="Minecraft",
                aliases=["minecraft", "mine"],
                genero="sandbox",
                fit_inicial=7,
            ),
        ]
        videos = [
            VideoColetado(
                titulo="Esse jogo de terror me quebrou",
                canal="Canal Referencia 1",
                plataforma="youtube",
                url="https://exemplo.com/video1",
                views=800000,
                likes=90000,
                comentarios=1200,
                data_publicacao="2026-05-15",
                texto_comentarios="qual nome do jogo? repo muito bom",
            ),
            VideoColetado(
                titulo="Minecraft mas tudo explode",
                canal="Canal Referencia 2",
                plataforma="tiktok",
                url="https://exemplo.com/video2",
                views=120000,
                likes=8000,
                comentarios=100,
                data_publicacao="2026-05-16",
                texto_comentarios="minecraft de novo",
            ),
        ]

        ranking = calcular_ranking(jogos, videos, canais)

        self.assertEqual(ranking[0].jogo.nome, "R.E.P.O.")
        self.assertGreater(ranking[0].score_final, ranking[1].score_final)
        self.assertEqual(ranking[0].videos_encontrados, 1)
        self.assertEqual(ranking[0].canais_diferentes, 1)
        self.assertGreater(ranking[0].score_descoberta, ranking[1].score_descoberta)

    def test_detecta_novas_frases_de_descoberta(self):
        jogo = JogoSeed(
            nome="R.E.P.O.",
            aliases=["repo"],
            genero="horror engracado",
            fit_inicial=9,
        )
        video = VideoColetado(
            titulo="Repo ficou famoso do nada",
            canal="Canal Referencia 1",
            plataforma="youtube",
            url="https://exemplo.com/video3",
            views=200000,
            likes=15000,
            comentarios=500,
            data_publicacao="2026-05-18",
            texto_comentarios="WHAT GAME? link do jogo steam?",
        )

        ranking = calcular_ranking([jogo], [video], [])

        self.assertGreater(ranking[0].score_descoberta, 0)

    def test_ranking_guarda_videos_associados_ao_jogo(self):
        jogo = JogoSeed(
            nome="R.E.P.O.",
            aliases=["repo"],
            genero="horror engracado",
            fit_inicial=9,
        )
        video = VideoColetado(
            titulo="Repo viralizou",
            canal="Core",
            plataforma="youtube",
            url="https://youtube.com/shorts/exemplo",
            views=800000,
            likes=90000,
            comentarios=1200,
            data_publicacao="2026-05-18",
            texto_comentarios="qual nome repo",
        )

        ranking = calcular_ranking([jogo], [video], [])

        self.assertEqual(ranking[0].videos, [video])

    def test_impressao_mostra_videos_que_influenciaram(self):
        jogo = JogoSeed(
            nome="R.E.P.O.",
            aliases=["repo"],
            genero="horror engracado",
            fit_inicial=9,
        )
        video = VideoColetado(
            titulo="Esse jogo de terror me quebrou",
            canal="Core",
            plataforma="youtube",
            url="https://youtube.com/shorts/exemplo",
            views=800000,
            likes=90000,
            comentarios=1200,
            data_publicacao="2026-05-18",
            texto_comentarios="qual nome repo",
        )
        ranking = calcular_ranking([jogo], [video], [])
        saida = StringIO()

        with redirect_stdout(saida):
            imprimir_ranking(ranking)

        texto = saida.getvalue()
        self.assertIn("Videos que influenciaram:", texto)
        self.assertIn("Core | youtube | 800000 views | Esse jogo de terror me quebrou", texto)
        self.assertIn("https://youtube.com/shorts/exemplo", texto)


if __name__ == "__main__":
    unittest.main()
