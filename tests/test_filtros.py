import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import _filtrar_por_data, _filtrar_por_plataforma, _montar_ranking
from modelos import JogoSeed, VideoColetado


# Cria um video de teste com valores padrao sobrescreviveis.
def _video(titulo="Alpha", plataforma="youtube", data="2026-05-10", views=100000):
    return VideoColetado(
        titulo=titulo,
        canal="Canal Teste",
        plataforma=plataforma,
        url=f"https://exemplo.com/{titulo}-{plataforma}-{data}-{views}",
        views=views,
        likes=1000,
        comentarios=100,
        data_publicacao=data,
        texto_comentarios="",
    )


# Cria um jogo seed de teste.
def _jogo(nome):
    return JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=8.0)


# --- Filtro por plataforma ---

# O filtro de plataforma mantem so a plataforma pedida, ignorando maiusculas/minusculas.
def test_filtra_por_plataforma_ignora_maiusculas():
    videos = [
        _video(plataforma="YouTube"),
        _video(plataforma="tiktok"),
        _video(plataforma="youtube"),
    ]

    filtrados = _filtrar_por_plataforma(videos, "youtube")

    assert [video.plataforma for video in filtrados] == ["YouTube", "youtube"]


# No ranking, --plataforma deixa entrar so os jogos da plataforma pedida.
def test_montar_ranking_aplica_filtro_de_plataforma():
    jogos = [_jogo("Alpha"), _jogo("Beta")]
    videos = [
        _video(titulo="Alpha", plataforma="youtube"),
        _video(titulo="Beta", plataforma="tiktok"),
    ]

    ranking = _montar_ranking(jogos, videos, [], plataforma="YouTube")

    assert [resultado.jogo.nome for resultado in ranking] == ["Alpha"]


# --- Limite --top ---

# --top corta o ranking nos N de maior score, descartando o resto.
def test_montar_ranking_aplica_limite_top():
    jogos = [_jogo("Alpha"), _jogo("Beta"), _jogo("Gamma")]
    videos = [
        _video(titulo="Alpha", views=900000),
        _video(titulo="Beta", views=500000),
        _video(titulo="Gamma", views=100000),
    ]

    ranking = _montar_ranking(jogos, videos, [], top=2)

    assert len(ranking) == 2
    assert "Gamma" not in [resultado.jogo.nome for resultado in ranking]


# --- Filtro --desde ---

# O filtro de data mantem videos a partir da data e ignora datas invalidas.
def test_filtra_por_data_mantem_recentes_e_ignora_invalida():
    videos = [
        _video(data="2026-05-15"),
        _video(data="2026-04-20"),
        _video(data="lixo"),
    ]

    filtrados = _filtrar_por_data(videos, date(2026, 5, 1))

    assert [video.data_publicacao for video in filtrados] == ["2026-05-15"]


# No ranking, --desde deixa entrar so os jogos com video a partir da data.
def test_montar_ranking_aplica_filtro_desde():
    hoje = date.today()
    recente = hoje.isoformat()
    antigo = (hoje - timedelta(days=120)).isoformat()
    jogos = [_jogo("Alpha"), _jogo("Beta")]
    videos = [
        _video(titulo="Alpha", data=recente),
        _video(titulo="Beta", data=antigo),
    ]

    ranking = _montar_ranking(jogos, videos, [], desde=hoje - timedelta(days=7))

    assert [resultado.jogo.nome for resultado in ranking] == ["Alpha"]
