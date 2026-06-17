import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, MeuVideo, VideoColetado
from ranker import (
    calcular_ranking,
    _ajuste_fit_real,
    _calcular_bonus_velocidade,
    _calcular_score_oportunidade,
    _gerar_acao_recomendada,
    peso_base_plataforma,
)
from main import imprimir_ranking
from metricas_video import calcular_views_por_dia
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

    def test_canal_mais_similar_influencia_mais_no_ranking(self):
        # Mesmo video (mesmos numeros e data), so muda o canal: o canal mais
        # parecido com o nicho tem peso_similaridade maior e deve puxar o jogo
        # para cima no ranking.
        canais = [
            CanalReferencia(
                nome="Canal Similar",
                plataforma="youtube",
                url="https://youtube.com/@similar",
                peso=1.0,
                nicho="gaming_humor",
                tipo_conteudo="gameplay",
                peso_similaridade=2.0,
            ),
            CanalReferencia(
                nome="Canal Distante",
                plataforma="youtube",
                url="https://youtube.com/@distante",
                peso=1.0,
                nicho="review_games",
                tipo_conteudo="review",
                peso_similaridade=1.0,
            ),
        ]
        jogos = [
            JogoSeed(nome="Repo", aliases=["repo"], genero="horror", fit_inicial=8),
            JogoSeed(nome="Mine", aliases=["mine"], genero="sandbox", fit_inicial=8),
        ]
        videos = [
            VideoColetado(
                titulo="repo gameplay",
                canal="Canal Similar",
                plataforma="youtube",
                url="https://exemplo.com/repo",
                views=300000,
                likes=20000,
                comentarios=800,
                data_publicacao="2026-05-20",
                texto_comentarios="repo muito bom",
            ),
            VideoColetado(
                titulo="mine gameplay",
                canal="Canal Distante",
                plataforma="youtube",
                url="https://exemplo.com/mine",
                views=300000,
                likes=20000,
                comentarios=800,
                data_publicacao="2026-05-20",
                texto_comentarios="mine muito bom",
            ),
        ]

        ranking = calcular_ranking(jogos, videos, canais)
        por_jogo = {resultado.jogo.nome: resultado for resultado in ranking}

        self.assertEqual(ranking[0].jogo.nome, "Repo")
        self.assertGreater(
            por_jogo["Repo"].score_tendencia, por_jogo["Mine"].score_tendencia
        )

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
        # views/dia depende da data de hoje, entao o valor esperado e calculado
        # com a mesma funcao central para o teste nao quebrar com o passar dos dias.
        views_por_dia = calcular_views_por_dia(video)
        self.assertIn(
            "Core | youtube | 800000 views | 90000 likes | 1200 comentarios | "
            f"11.4% engajamento | {views_por_dia:.0f} views/dia | "
            "2026-05-18 | Esse jogo de terror me quebrou",
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


# Pesos por plataforma: valores da tabela, case-insensitive e neutro para desconhecida.
def test_peso_base_plataforma():
    assert peso_base_plataforma("youtube") == 1.0
    assert peso_base_plataforma("YouTube") == 1.0
    assert peso_base_plataforma("shorts") == 0.9
    assert peso_base_plataforma(" TikTok ") == 0.8
    assert peso_base_plataforma("instagram") == 0.8
    assert peso_base_plataforma("twitch") == 1.0


# Mesmos numeros em plataformas diferentes: o video do YouTube deve pesar mais.
def test_ranking_pesa_views_do_youtube_mais_que_tiktok():
    hoje = date.today().isoformat()

    jogo_youtube = JogoSeed(nome="Game Youtube", aliases=[], genero="terror", fit_inicial=8.0)
    jogo_tiktok = JogoSeed(nome="Game Tiktok", aliases=[], genero="terror", fit_inicial=8.0)

    video_youtube = VideoColetado(
        titulo="Game Youtube viralizou",
        canal="Canal Teste",
        plataforma="youtube",
        url="https://youtube.com/igual",
        views=100000,
        likes=1000,
        comentarios=100,
        data_publicacao=hoje,
        texto_comentarios="",
    )
    video_tiktok = VideoColetado(
        titulo="Game Tiktok viralizou",
        canal="Canal Teste",
        plataforma="tiktok",
        url="https://tiktok.com/igual",
        views=100000,
        likes=1000,
        comentarios=100,
        data_publicacao=hoje,
        texto_comentarios="",
    )

    ranking = calcular_ranking(
        [jogo_youtube, jogo_tiktok],
        [video_youtube, video_tiktok],
        [],
    )

    assert ranking[0].jogo.nome == "Game Youtube"
    assert ranking[0].score_tendencia > ranking[1].score_tendencia


# Formula da oportunidade: tendencia*0.40 + saturacao*0.40 + descoberta*0.20.
def test_score_oportunidade_combina_sinais():
    assert _calcular_score_oportunidade(100.0, 90.0, 50.0) == 86.0
    assert _calcular_score_oportunidade(0.0, 0.0, 0.0) == 0.0


# O ranking preenche score_oportunidade coerente com os proprios sub-scores.
def test_ranking_preenche_score_oportunidade():
    jogo = JogoSeed(nome="Game Oportuno", aliases=[], genero="terror", fit_inicial=8.0)
    video = VideoColetado(
        titulo="Game Oportuno viralizou",
        canal="Canal Teste",
        plataforma="youtube",
        url="https://youtube.com/oportuno",
        views=100000,
        likes=1000,
        comentarios=100,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )

    resultado = calcular_ranking([jogo], [video], [])[0]

    esperado = round(
        _calcular_score_oportunidade(
            resultado.score_tendencia,
            resultado.score_saturacao,
            resultado.score_descoberta,
        ),
        1,
    )
    assert resultado.score_oportunidade == esperado
    assert resultado.score_oportunidade > 0


# Alta oportunidade (poucos canais + engajamento alto) vira o motivo principal.
def test_motivo_destaca_oportunidade():
    jogo = JogoSeed(nome="Game Janela", aliases=[], genero="terror", fit_inicial=8.0)
    video = VideoColetado(
        titulo="Game Janela explodiu do nada",
        canal="Canal Unico",
        plataforma="youtube",
        url="https://youtube.com/janela",
        views=100000,
        likes=9000,
        comentarios=1500,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )

    resultado = calcular_ranking([jogo], [video], [])[0]

    assert "oportunidade antes da saturacao" in resultado.motivo


# Alta tendencia mas muitos canais: o motivo avisa que precisa de angulo diferente.
def test_motivo_avisa_jogo_saturado():
    jogo = JogoSeed(nome="Game Saturado", aliases=[], genero="terror", fit_inicial=8.0)
    data_antiga = (date.today() - timedelta(days=120)).isoformat()
    videos = [
        VideoColetado(
            titulo=f"Game Saturado no canal {indice}",
            canal=f"Canal {indice}",
            plataforma="youtube",
            url=f"https://youtube.com/saturado-{indice}",
            views=600000,
            likes=100,
            comentarios=10,
            data_publicacao=data_antiga,
            texto_comentarios="",
        )
        for indice in range(4)
    ]

    resultado = calcular_ranking([jogo], videos, [])[0]

    assert "angulo diferente" in resultado.motivo


# Fit alto com um unico video fraco: o motivo admite a pouca evidencia.
def test_motivo_indica_pouca_evidencia():
    jogo_forte = JogoSeed(nome="Game Forte", aliases=[], genero="terror", fit_inicial=8.0)
    jogo_fraco = JogoSeed(nome="Game Fraco", aliases=[], genero="terror", fit_inicial=9.0)
    data_antiga = (date.today() - timedelta(days=120)).isoformat()

    video_forte = VideoColetado(
        titulo="Game Forte viralizou",
        canal="Canal A",
        plataforma="youtube",
        url="https://youtube.com/forte",
        views=800000,
        likes=50000,
        comentarios=2000,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )
    video_fraco = VideoColetado(
        titulo="Game Fraco apareceu uma vez",
        canal="Canal B",
        plataforma="youtube",
        url="https://youtube.com/fraco",
        views=5000,
        likes=5,
        comentarios=0,
        data_publicacao=data_antiga,
        texto_comentarios="",
    )

    ranking = calcular_ranking([jogo_forte, jogo_fraco], [video_forte, video_fraco], [])
    resultado_fraco = next(r for r in ranking if r.jogo.nome == "Game Fraco")

    assert "pouca evidencia" in resultado_fraco.motivo


# Uma acao por regra, na ordem de prioridade (veto por saturacao primeiro).
def test_acao_recomendada_cobre_as_regras():
    # saturacao <= 40 veta, mesmo com oportunidade e fit altos
    assert (
        _gerar_acao_recomendada(80.0, 90.0, 40.0, 100.0, 5)
        == "Evitar por saturacao alta"
    )
    # oportunidade alta + fit alto = aposta maxima
    assert (
        _gerar_acao_recomendada(80.0, 90.0, 90.0, 100.0, 3)
        == "Priorizar para video longo"
    )
    # oportunidade alta sem fit = validar barato
    assert _gerar_acao_recomendada(80.0, 60.0, 90.0, 100.0, 3) == "Testar em Short"
    # um video so e tendencia fraca = falta evidencia
    assert (
        _gerar_acao_recomendada(50.0, 90.0, 90.0, 30.0, 1)
        == "Pesquisar mais videos antes de gravar"
    )
    # caso neutro = observar
    assert (
        _gerar_acao_recomendada(50.0, 60.0, 75.0, 80.0, 3)
        == "Monitorar por mais alguns dias"
    )


# O ranking preenche acao_recomendada (nunca sai vazia).
def test_ranking_preenche_acao_recomendada():
    jogo = JogoSeed(nome="Game Acao", aliases=[], genero="terror", fit_inicial=9.0)
    video = VideoColetado(
        titulo="Game Acao viralizou",
        canal="Canal Teste",
        plataforma="youtube",
        url="https://youtube.com/acao",
        views=100000,
        likes=9000,
        comentarios=1500,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )

    resultado = calcular_ranking([jogo], [video], [])[0]

    assert resultado.acao_recomendada == "Priorizar para video longo"


# --- Sprint 9.2: fit real do canal ajusta o score final de forma leve ---

# Meu video com data antiga: o score_resultado_real fica deterministico (volume +
# engajamento), sem depender da data de hoje. forte ~66, fraco ~4.
def _meu_video_fit(jogo, video_id, views, likes, comentarios, tipo="longo"):
    return MeuVideo(
        video_id=video_id,
        titulo=f"meu {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video=tipo,
    )


def _jogo_e_video_simples():
    jogo = JogoSeed(nome="Repo", aliases=["repo"], genero="terror", fit_inicial=8.0)
    video = VideoColetado(
        titulo="repo viralizou",
        canal="Canal",
        plataforma="youtube",
        url="https://youtube.com/repo",
        views=100000,
        likes=9000,
        comentarios=1500,
        data_publicacao=date.today().isoformat(),
        texto_comentarios="",
    )
    return jogo, video


def test_ajuste_fit_real_e_leve_e_limitado():
    assert _ajuste_fit_real(None) == 0.0
    assert _ajuste_fit_real(45.0) == 0.0   # zona morta
    assert _ajuste_fit_real(60.0) == 0.0   # limiar do bonus
    assert _ajuste_fit_real(30.0) == 0.0   # limiar da penalidade
    assert _ajuste_fit_real(100.0) == 5.0
    assert _ajuste_fit_real(0.0) == -5.0
    assert abs(_ajuste_fit_real(80.0) - 2.5) < 1e-9


def test_fit_real_alto_da_bonus_leve_no_score_final():
    jogo, video = _jogo_e_video_simples()
    base = calcular_ranking([jogo], [video], [])[0]

    meus = [_meu_video_fit("Repo", "m1", 900000, 120000, 8000)]  # forte ~66
    com_fit = calcular_ranking([jogo], [video], [], meus)[0]

    assert com_fit.score_fit_real is not None
    assert com_fit.score_final > base.score_final
    assert com_fit.score_final - base.score_final <= 5.0  # ajuste leve


def test_fit_real_muito_baixo_da_penalidade_leve():
    jogo, video = _jogo_e_video_simples()
    base = calcular_ranking([jogo], [video], [])[0]

    meus = [_meu_video_fit("Repo", "m1", 80000, 200, 50)]  # fraco ~4
    com_fit = calcular_ranking([jogo], [video], [], meus)[0]

    assert com_fit.score_final < base.score_final
    assert base.score_final - com_fit.score_final <= 5.0


def test_fit_real_sem_historico_mantem_score():
    jogo, video = _jogo_e_video_simples()
    base = calcular_ranking([jogo], [video], [])[0]

    meus = [_meu_video_fit("Outro Jogo", "m1", 900000, 120000, 8000)]
    com_fit = calcular_ranking([jogo], [video], [], meus)[0]

    assert com_fit.score_fit_real is None
    assert com_fit.score_final == base.score_final


def test_ranking_calibra_formato_pelo_historico():
    jogo, video = _jogo_e_video_simples()  # acao do ranking aponta "longo"

    meus = [_meu_video_fit("Repo", "m1", 900000, 120000, 8000, tipo="curto")]  # curto forte
    resultado = calcular_ranking([jogo], [video], [], meus)[0]

    assert resultado.formato_sugerido == "curto"


def test_ranking_sem_historico_usa_formato_da_acao():
    jogo, video = _jogo_e_video_simples()

    resultado = calcular_ranking([jogo], [video], [])[0]

    assert resultado.formato_sugerido == "longo"  # vem da acao "Priorizar para video longo"


if __name__ == "__main__":
    unittest.main()
