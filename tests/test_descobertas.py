import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from descobertas import descobertas_sem_jogo
from modelos import JogoSeed, VideoColetado


def _jogos():
    return [JogoSeed(nome="Roblox", aliases=["roblox"], genero="", fit_inicial=5.0)]


def _video(titulo="t", descricao="", comentarios="", views=1000, canal="Lozao", url="https://y/1"):
    video = VideoColetado(
        titulo=titulo,
        canal=canal,
        plataforma="youtube",
        url=url,
        views=views,
        likes=10,
        comentarios=5,
        data_publicacao="2026-08-01",
        texto_comentarios=comentarios,
    )
    video.descricao = descricao
    return video


def test_video_com_pergunta_e_sem_jogo_entra_na_lista():
    videos = [_video(titulo="MATAR O VERITY", comentarios="qual o nome do jogo", views=724559)]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert len(achados) == 1
    assert achados[0].views == 724559
    assert achados[0].perguntas == 1
    assert achados[0].candidato == ""
    assert achados[0].url == "https://y/1"


def test_video_com_jogo_identificado_fica_de_fora():
    videos = [_video(titulo="joguei Roblox", comentarios="qual o nome do jogo")]

    assert descobertas_sem_jogo(videos, _jogos()) == []


def test_video_sem_sinal_de_descoberta_fica_de_fora():
    videos = [_video(titulo="sem pista", comentarios="video muito bom")]

    assert descobertas_sem_jogo(videos, _jogos()) == []


def test_candidato_da_descricao_aparece_na_lista():
    videos = [
        _video(
            titulo="MEU BARCO NAUFRAGO",
            descricao="nesse video eu trouxe um jogo chamado The lacerator",
            comentarios="que jogo e esse",
        )
    ]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert achados[0].candidato == "The lacerator"


def test_ordena_por_alcance_decrescente():
    videos = [
        _video(titulo="a", comentarios="qual o nome do jogo", views=100, url="https://y/a"),
        _video(titulo="b", comentarios="qual o nome do jogo", views=900, url="https://y/b"),
    ]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert [d.views for d in achados] == [900, 100]


def test_conta_mais_de_uma_pergunta_no_mesmo_video():
    videos = [_video(titulo="x", comentarios="qual o nome do jogo e onde baixa")]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert achados[0].perguntas >= 2


def test_lista_vazia_quando_nao_ha_video():
    assert descobertas_sem_jogo([], _jogos()) == []
