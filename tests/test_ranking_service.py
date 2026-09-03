import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, VideoColetado
from ranking_service import carregar_ranking, filtrar_por_data, filtrar_por_plataforma, montar_ranking


def _video(plataforma="youtube", dias_atras=0, titulo="Video"):
    data = (date.today() - timedelta(days=dias_atras)).isoformat()
    return VideoColetado(
        titulo=titulo, canal="Canal", plataforma=plataforma,
        url=f"https://y/{titulo}", views=1000, likes=10, comentarios=1,
        data_publicacao=data, texto_comentarios="",
    )


def test_filtrar_por_plataforma_ignora_maiusculas():
    videos = [_video(plataforma="YouTube"), _video(plataforma="TikTok")]
    filtrados = filtrar_por_plataforma(videos, "youtube")
    assert len(filtrados) == 1
    assert filtrados[0].plataforma == "YouTube"


def test_filtrar_por_data_mantem_so_a_partir_da_data():
    videos = [_video(dias_atras=1), _video(dias_atras=10)]
    filtrados = filtrar_por_data(videos, date.today() - timedelta(days=5))
    assert len(filtrados) == 1


def test_montar_ranking_aplica_top():
    jogos = [
        JogoSeed(nome="Jogo A", aliases=["jogo a"], genero="", fit_inicial=5),
        JogoSeed(nome="Jogo B", aliases=["jogo b"], genero="", fit_inicial=5),
    ]
    videos = [_video(titulo="jogo a"), _video(titulo="jogo b")]
    ranking = montar_ranking(jogos, videos, [], top=1)
    assert len(ranking) == 1


def test_carregar_ranking_le_csvs_do_diretorio(tmp_path):
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRepo,repo,terror,8\n", encoding="utf-8"
    )
    (tmp_path / "canais_referencia.csv").write_text(
        "nome,plataforma,url,peso\nCanal,youtube,https://y/c,1.0\n", encoding="utf-8"
    )
    videos_csv = tmp_path / "videos.csv"
    videos_csv.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios\n"
        "Repo e incrivel,Canal,youtube,https://y/1,1000,10,1,2026-05-01,\n",
        encoding="utf-8",
    )
    meus_videos_csv = tmp_path / "meus_videos.csv"

    ranking = carregar_ranking(tmp_path, videos_csv, meus_videos_csv)

    assert len(ranking) == 1
    assert ranking[0].jogo.nome == "Repo"
