import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, VideoColetado
from ranker import calcular_ranking


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


if __name__ == "__main__":
    unittest.main()
