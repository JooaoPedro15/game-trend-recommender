import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import CanalReferencia, JogoSeed, MeuVideo, VideoColetado
from validacao_dados import validar_dados


def _jogo(nome="Repo", aliases=("repo",)):
    return JogoSeed(nome=nome, aliases=list(aliases), genero="terror", fit_inicial=8.0)


def _video(titulo="Repo viralizou", views=100000, data="2026-05-01", tipo="curto"):
    return VideoColetado(
        titulo=titulo,
        canal="Canal A",
        plataforma="youtube",
        url="https://y/1",
        views=views,
        likes=9000,
        comentarios=500,
        data_publicacao=data,
        texto_comentarios="",
        tipo_video=tipo,
    )


def _canal(nicho="gaming_humor", peso_similaridade=2.0):
    return CanalReferencia(
        nome="Canal A",
        plataforma="youtube",
        url="https://y/c",
        peso=1.0,
        nicho=nicho,
        tipo_conteudo="gameplay",
        peso_similaridade=peso_similaridade,
    )


def _meu(views=900000):
    return MeuVideo(
        video_id="m1",
        titulo="meu video",
        url="https://youtu.be/m1",
        data_publicacao="2020-01-01",
        jogo_detectado="Repo",
        confianca_jogo="media",
        fonte_deteccao="titulo",
        views=views,
        likes=10000,
        comentarios=500,
        tipo_video="curto",
    )


def _severidades(problemas):
    return {p.severidade for p in problemas}


def _mensagens(problemas):
    return " | ".join(p.mensagem for p in problemas)


def test_dados_limpos_sem_problemas():
    problemas = validar_dados(
        [_video()], [_jogo()], [_canal()], [_meu()],
        chave_configurada=True, canal_configurado=True,
    )
    assert problemas == []


def test_sem_jogos_e_critico():
    problemas = validar_dados(
        [_video()], [], [_canal()], [], chave_configurada=True, canal_configurado=True
    )
    assert "critico" in _severidades(problemas)
    assert "jogos_seed" in _mensagens(problemas)


def test_sem_videos_e_critico():
    problemas = validar_dados(
        [], [_jogo()], [_canal()], [], chave_configurada=True, canal_configurado=True
    )
    assert any(p.severidade == "critico" and "video" in p.mensagem.lower() for p in problemas)


def test_todos_os_videos_sem_jogo_e_critico():
    # titulo nao casa com nenhum jogo do seed
    videos = [_video(titulo="passeando sem jogo nenhum")]
    problemas = validar_dados(
        videos, [_jogo()], [_canal()], [], chave_configurada=True, canal_configurado=True
    )
    assert any(p.severidade == "critico" and "detectado" in p.mensagem for p in problemas)


def test_views_zeradas_e_sem_data_viram_aviso():
    videos = [_video(), _video(views=0), _video(data="data-ruim")]
    problemas = validar_dados(
        videos, [_jogo()], [_canal()], [], chave_configurada=True, canal_configurado=True
    )
    mensagens = _mensagens(problemas)
    assert "views zeradas" in mensagens
    assert "sem data valida" in mensagens
    assert "aviso" in _severidades(problemas)


def test_tipo_video_desconhecido_demais_e_aviso():
    videos = [_video(tipo="desconhecido"), _video(titulo="Repo de novo", tipo="desconhecido")]
    problemas = validar_dados(
        videos, [_jogo()], [_canal()], [], chave_configurada=True, canal_configurado=True
    )
    assert any(p.severidade == "aviso" and "tipo_video desconhecido" in p.mensagem for p in problemas)


def test_jogos_sem_alias_e_info():
    problemas = validar_dados(
        [_video()], [_jogo(aliases=())], [_canal()], [],
        chave_configurada=True, canal_configurado=True,
    )
    assert any(p.severidade == "info" and "aliases" in p.mensagem for p in problemas)


def test_canais_sem_nicho_e_similaridade_neutra():
    canais = [_canal(nicho="desconhecido", peso_similaridade=1.0)]
    problemas = validar_dados(
        [_video()], [_jogo()], canais, [], chave_configurada=True, canal_configurado=True
    )
    mensagens = _mensagens(problemas)
    assert "sem nicho" in mensagens
    assert "evidencia de nicho fica desligada" in mensagens


def test_env_ausente_vira_info():
    problemas = validar_dados(
        [_video()], [_jogo()], [_canal()], [],
        chave_configurada=False, canal_configurado=False,
    )
    mensagens = _mensagens(problemas)
    assert "YOUTUBE_API_KEY" in mensagens
    assert "MEU_CANAL_YOUTUBE_ID" in mensagens
    assert all(p.severidade == "info" for p in problemas if "configurad" in p.mensagem)
