import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, MeuVideo, ResultadoRecomendacao, VideoColetado
from relatorio_diario import gerar_relatorio_diario_markdown


def _video(canal, url, views=800000, likes=90000, comentarios=1500):
    return VideoColetado(
        titulo=f"{canal} jogou",
        canal=canal,
        plataforma="youtube",
        url=url,
        views=views,
        likes=likes,
        comentarios=comentarios,
        data_publicacao="2026-05-20",
        texto_comentarios="qual o nome do jogo",
    )


def _rec(nome, score_final, oportunidade, saturacao, evidencia, videos):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=8.0),
        score_final=score_final,
        score_tendencia=80.0,
        score_fit_canal=80.0,
        score_descoberta=60.0,
        score_saturacao=saturacao,
        videos_encontrados=len(videos),
        canais_diferentes=len({v.canal for v in videos}),
        motivo="",
        videos=videos,
        score_oportunidade=oportunidade,
        acao_recomendada="Repetir teste",
        score_evidencia_criadores=evidencia,
        formato_sugerido="curto",
    )


def _meu(jogo, video_id, views, likes, comentarios):
    return MeuVideo(
        video_id=video_id,
        titulo=f"meu video {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="media" if jogo else "nao_detectado",
        fonte_deteccao="titulo" if jogo else "nao_detectado",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video="curto",
    )


def _cenario():
    ranking = [
        _rec("Repo", 90, 80, 90, 85.0, [_video("Canal A", "https://y/a")]),
        _rec("Mine", 60, 40, 90, 40.0, [_video("Canal B", "https://y/b", views=50000, likes=100, comentarios=5)]),
    ]
    canais = [
        CanalReferencia(nome="Canal A", plataforma="youtube", url="https://y/ca", peso=1.0),
        CanalReferencia(nome="Canal B", plataforma="youtube", url="https://y/cb", peso=1.0),
    ]
    meus = [
        _meu("Repo", "re", 900000, 120000, 8000),  # forte: vira candidato a repetir
        _meu("", "semjogo", 300000, 9000, 200),     # sem jogo detectado
    ]
    return ranking, meus, canais


def test_relatorio_diario_tem_todas_as_secoes(tmp_path):
    caminho = tmp_path / "relatorio_diario.md"
    ranking, meus, canais = _cenario()

    gerar_relatorio_diario_markdown(caminho, ranking, meus, canais)

    texto = caminho.read_text(encoding="utf-8")
    assert "# Relatorio Diario" in texto
    assert "## Top jogos recomendados" in texto
    assert "## Top oportunidades" in texto
    assert "## Jogos para repetir" in texto
    assert "## Jogos que prometiam mas nao funcionaram" in texto
    assert "## Meus videos sem jogo detectado" in texto
    assert "## Evidencias principais de criadores" in texto
    assert "## Links uteis para assistir" in texto
    assert "## Observacoes operacionais" in texto


def test_relatorio_diario_classifica_e_lista(tmp_path):
    caminho = tmp_path / "relatorio_diario.md"
    ranking, meus, canais = _cenario()

    gerar_relatorio_diario_markdown(caminho, ranking, meus, canais)

    texto = caminho.read_text(encoding="utf-8")
    # Repo (forte comigo + janela aberta) entra em "repetir"
    repetir = texto.split("## Jogos para repetir")[1].split("##")[0]
    assert "Repo" in repetir
    # video sem jogo aparece com link
    sem = texto.split("## Meus videos sem jogo detectado")[1].split("##")[0]
    assert "https://youtu.be/semjogo" in sem
    # link util de criador para o jogo de maior evidencia
    links = texto.split("## Links uteis para assistir")[1].split("##")[0]
    assert "https://y/a" in links
    # observacao operacional sobre videos sem jogo
    obs = texto.split("## Observacoes operacionais")[1]
    assert "meus_videos_sem_jogo" in obs


def test_relatorio_diario_vazio(tmp_path):
    caminho = tmp_path / "vazio.md"

    gerar_relatorio_diario_markdown(caminho, [], [], [])

    texto = caminho.read_text(encoding="utf-8")
    assert "# Relatorio Diario" in texto
    assert "(ranking vazio)" in texto
    assert "coletar_meu_canal" in texto  # observacao: sem dados do canal
