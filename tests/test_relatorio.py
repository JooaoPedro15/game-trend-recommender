import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, ResultadoRecomendacao, VideoColetado
from relatorio import gerar_relatorio_markdown


# Garante que gerar_relatorio_markdown cria um .md com as informacoes principais do ranking.
def test_gera_relatorio_markdown_com_informacoes_principais(tmp_path):
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
    jogo = JogoSeed(
        nome="R.E.P.O.",
        aliases=["repo"],
        genero="horror engracado",
        fit_inicial=9,
    )
    resultado = ResultadoRecomendacao(
        jogo=jogo,
        score_final=82.0,
        score_tendencia=70.0,
        score_fit_canal=90.0,
        score_descoberta=50.0,
        score_saturacao=90.0,
        videos_encontrados=1,
        canais_diferentes=1,
        motivo="Jogo apareceu em video recente com alto engajamento.",
        videos=[video],
        score_oportunidade=74.0,
    )

    caminho = tmp_path / "ranking.md"
    gerar_relatorio_markdown(caminho, [resultado])

    assert caminho.exists()

    conteudo = caminho.read_text(encoding="utf-8")
    assert "# Ranking de Games Recomendados" in conteudo
    assert "R.E.P.O." in conteudo
    assert "Score final: 82.0" in conteudo
    assert "Oportunidade: 74.0" in conteudo
    assert "Jogo apareceu em video recente com alto engajamento." in conteudo
    assert "800000 views" in conteudo
    assert "11.4% engajamento" in conteudo
    assert "views/dia" in conteudo
