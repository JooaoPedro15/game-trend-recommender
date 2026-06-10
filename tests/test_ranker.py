import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, VideoColetado
from ranker import calcular_ranking, _calcular_bonus_velocidade
from main import imprimir_ranking
from datetime import date, timedelta



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
        self.assertIn(
            "Core | youtube | 800000 views | 90000 likes | 1200 comentarios | "
            "11.4% engajamento | 2026-05-18 | Esse jogo de terror me quebrou",
            texto,
        )
        self.assertIn("https://youtube.com/shorts/exemplo", texto)

# Testa se videos recentes influenciam mais o ranking que videos antigos.
def test_ranking_prioriza_video_mais_recente():
    hoje = date.today()
    data_recente = hoje.isoformat()
    data_antiga = (hoje - timedelta(days=120)).isoformat()

    jogo_recente = JogoSeed(
        nome="Game Recente",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    jogo_antigo = JogoSeed(
        nome="Game Antigo",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    video_recente = VideoColetado(
        titulo="Game Recente viralizou",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/recente",
        views=100000,
        likes=10000,
        comentarios=500,
        data_publicacao=data_recente,
        texto_comentarios="",
    )

    video_antigo = VideoColetado(
        titulo="Game Antigo viralizou",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/antigo",
        views=100000,
        likes=10000,
        comentarios=500,
        data_publicacao=data_antiga,
        texto_comentarios="",
    )

    canais = [
        CanalReferencia(
            nome="Canal Teste",
            plataforma="YouTube",
            url="https://youtube.com/canal",
            peso=1.0,
        )
    ]

    ranking = calcular_ranking(
        [jogo_recente, jogo_antigo],
        [video_recente, video_antigo],
        canais,
    )

    assert ranking[0].jogo.nome == "Game Recente"

    # Testa se um video com maior engajamento pode superar um video com mais views.
def test_ranking_prioriza_video_com_maior_engajamento():
    hoje = date.today().isoformat()

    jogo_mais_views = JogoSeed(
        nome="Game Mais Views",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    jogo_mais_engajamento = JogoSeed(
        nome="Game Mais Engajamento",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    video_mais_views = VideoColetado(
        titulo="Game Mais Views viralizou",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/mais-views",
        views=100000,
        likes=1000,
        comentarios=10,
        data_publicacao=hoje,
        texto_comentarios="",
    )

    video_mais_engajamento = VideoColetado(
        titulo="Game Mais Engajamento viralizou",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/mais-engajamento",
        views=60000,
        likes=10000,
        comentarios=1000,
        data_publicacao=hoje,
        texto_comentarios="",
    )

    canais = [
        CanalReferencia(
            nome="Canal Teste",
            plataforma="YouTube",
            url="https://youtube.com/canal",
            peso=1.0,
        )
    ]

    ranking = calcular_ranking(
        [jogo_mais_views, jogo_mais_engajamento],
        [video_mais_views, video_mais_engajamento],
        canais,
    )

    assert ranking[0].jogo.nome == "Game Mais Engajamento"


def test_ranking_prioriza_video_com_alta_velocidade_sobre_video_antigo_parecido():
    hoje = date.today()

    jogo_rapido = JogoSeed(
        nome="Game Rapido",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    jogo_antigo = JogoSeed(
        nome="Game Antigo",
        aliases=[],
        genero="terror",
        fit_inicial=8.0,
    )

    video_rapido = VideoColetado(
        titulo="Game Rapido viralizou hoje",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/rapido",
        views=100000,
        likes=0,
        comentarios=0,
        data_publicacao=hoje.isoformat(),
        texto_comentarios="",
    )

    video_antigo = VideoColetado(
        titulo="Game Antigo cresceu devagar",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/antigo-parecido",
        views=220000,
        likes=0,
        comentarios=0,
        data_publicacao=(hoje - timedelta(days=120)).isoformat(),
        texto_comentarios="",
    )

    ranking = calcular_ranking(
        [jogo_rapido, jogo_antigo],
        [video_rapido, video_antigo],
        [],
    )

    assert ranking[0].jogo.nome == "Game Rapido"


def test_bonus_velocidade_nao_ultrapassa_metade_das_views():
    video = VideoColetado(
        titulo="Game rapido demais",
        canal="Canal Teste",
        plataforma="YouTube",
        url="https://youtube.com/rapido-demais",
        views=100000,
        likes=0,
        comentarios=0,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )

    assert _calcular_bonus_velocidade(video) == 50000.0


if __name__ == "__main__":
    unittest.main()
