import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from diagnostico_dados import gerar_diagnostico
from modelos import JogoSeed, VideoColetado


# Cria um video de teste com valores padrao sobrescreviveis.
def _video(titulo="Jogo", canal="Canal A", plataforma="youtube", url="https://x/1", views=100, data="2026-05-01"):
    return VideoColetado(
        titulo=titulo,
        canal=canal,
        plataforma=plataforma,
        url=url,
        views=views,
        likes=1,
        comentarios=1,
        data_publicacao=data,
        texto_comentarios="",
    )


# Cria um jogo seed de teste.
def _jogo(nome, aliases=None):
    return JogoSeed(nome=nome, aliases=aliases or [], genero="terror", fit_inicial=8.0)


def test_conta_total_de_videos():
    videos = [_video(url="https://x/1"), _video(url="https://x/2"), _video(url="https://x/3")]

    diag = gerar_diagnostico(videos, [])

    assert diag.total == 3


def test_conta_videos_por_plataforma():
    videos = [
        _video(plataforma="YouTube", url="https://x/1"),
        _video(plataforma="youtube", url="https://x/2"),
        _video(plataforma="tiktok", url="https://x/3"),
        _video(plataforma="tiktok", url="https://x/4"),
    ]

    diag = gerar_diagnostico(videos, [])

    assert diag.por_plataforma == {"YouTube": 1, "youtube": 1, "tiktok": 2}


def test_conta_views_zeradas():
    videos = [
        _video(views=1000, url="https://x/1"),
        _video(views=0, url="https://x/2"),
        _video(views=0, url="https://x/3"),
    ]

    diag = gerar_diagnostico(videos, [])

    assert diag.views_zeradas == 2


def test_conta_videos_sem_data_publicacao():
    videos = [
        _video(data="2026-05-01", url="https://x/1"),
        _video(data="", url="https://x/2"),
        _video(data="   ", url="https://x/3"),
    ]

    diag = gerar_diagnostico(videos, [])

    assert diag.sem_data_publicacao == 2


def test_conta_sem_jogo_detectado_e_jogos_detectados():
    jogos = [_jogo("Repo", ["repo"]), _jogo("Minecraft")]
    videos = [
        _video(titulo="Repo gameplay", url="https://x/1"),
        _video(titulo="Repo de novo", url="https://x/2"),
        _video(titulo="Minecraft demais", url="https://x/3"),
        _video(titulo="Sem jogo aqui", url="https://x/4"),
        _video(titulo="Outro qualquer", url="https://x/5"),
    ]

    diag = gerar_diagnostico(videos, jogos)

    assert diag.sem_jogo_detectado == 2
    assert diag.jogos_detectados == {"Repo": 2, "Minecraft": 1}
