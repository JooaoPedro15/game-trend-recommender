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


def _sugestoes(problemas):
    return " | ".join(p.sugestao for p in problemas)


def test_dados_limpos_sem_problemas():
    video = _video()
    video.descricao = "descricao do video"
    problemas = validar_dados(
        [video], [_jogo()], [_canal()], [_meu()],
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


# --- Meus videos sem jogo detectado: a calibracao inteira depende disso ---
#
# Regressao: com 26 videos e nenhum jogo detectado, a validacao respondia
# "Nenhum problema encontrado" porque so olhava views zeradas.

def _meu_video(
    video_id="V1",
    jogo="Lethal Company",
    views=1000,
    jogo_no_seed=True,
    motivo_nao_detectado="",
):
    return MeuVideo(
        video_id=video_id,
        titulo="titulo",
        url=f"https://y/{video_id}",
        data_publicacao="2026-05-01",
        jogo_detectado=jogo,
        confianca_jogo="alta",
        fonte_deteccao="titulo",
        views=views,
        likes=10,
        comentarios=2,
        jogo_no_seed=jogo_no_seed,
        motivo_nao_detectado=motivo_nao_detectado,
    )


def _validar(meus_videos, colunas_faltando=None):
    return validar_dados(
        [_video()],
        [_jogo()],
        [_canal()],
        meus_videos,
        chave_configurada=True,
        canal_configurado=True,
        colunas_faltando_meus_videos=colunas_faltando,
    )


def test_todos_meus_videos_sem_jogo_e_critico():
    problemas = _validar([_meu_video(jogo=""), _meu_video("V2", jogo="")])

    assert "critico" in _severidades(problemas)
    assert "Nenhum dos 2 video(s) do meu canal tem jogo detectado" in _mensagens(problemas)


def test_parte_dos_meus_videos_sem_jogo_e_aviso():
    problemas = _validar([_meu_video(), _meu_video("V2", jogo="")])

    assert "critico" not in _severidades(problemas)
    assert "1 de 2 video(s) do meu canal sem jogo detectado" in _mensagens(problemas)


def test_todos_meus_videos_com_jogo_nao_gera_problema():
    problemas = _validar([_meu_video(), _meu_video("V2")])

    assert "sem jogo detectado" not in _mensagens(problemas)


def test_jogo_detectado_fora_do_seed_vira_aviso():
    problemas = _validar([_meu_video(jogo="Peak", jogo_no_seed=False)])

    assert "nao esta no" in _mensagens(problemas)


# --- Schema antigo do CSV: colunas ausentes viram aviso, nao silencio ---

def test_colunas_faltando_viram_aviso():
    problemas = _validar([_meu_video()], colunas_faltando=["descricao", "tags"])

    assert "aviso" in _severidades(problemas)
    assert "descricao, tags" in _mensagens(problemas)


def test_sem_colunas_faltando_nao_reclama_do_formato():
    problemas = _validar([_meu_video()], colunas_faltando=[])

    assert "coluna(s) do formato atual" not in _mensagens(problemas)


# --- Linhas coletadas antes do formato atual: o cabecalho ja esta certo, a linha nao ---
#
# O detector sempre grava um motivo_nao_detectado quando nao acha jogo. Entao "sem jogo E
# sem motivo" so acontece em linha que nunca passou pela deteccao atual — o sinal exato de
# coleta antiga, que a checagem de colunas_faltando nao enxerga depois da migracao.

def test_video_sem_jogo_e_sem_motivo_vira_aviso_de_coleta_antiga():
    problemas = _validar([_meu_video(jogo="", motivo_nao_detectado="")])

    assert "aviso" in _severidades(problemas)
    assert "coleta antiga" in _mensagens(problemas)
    assert "--forcar" in _sugestoes(problemas)


def test_video_sem_jogo_mas_com_motivo_nao_e_coleta_antiga():
    problemas = _validar(
        [_meu_video(jogo="", motivo_nao_detectado="nenhum_jogo_do_seed_encontrado_nas_fontes")]
    )

    assert "coleta antiga" not in _mensagens(problemas)


def test_video_com_jogo_detectado_nao_e_coleta_antiga():
    problemas = _validar([_meu_video()])

    assert "coleta antiga" not in _mensagens(problemas)


# --- Fora do seed vem do seed, nao da coluna gravada no CSV ---
#
# jogo_no_seed e gravado na hora da coleta e nunca mais muda. Depois de cadastrar o jogo
# com adicionar_jogo, a linha antiga continua dizendo "nao" e o aviso continuaria vivo
# para sempre. A pergunta certa e feita ao jogos_seed.csv, que e a fonte da verdade.

def test_jogo_ja_cadastrado_no_seed_para_de_ser_reportado():
    # A linha ainda carrega jogo_no_seed=False (coletada antes do cadastro), mas o jogo
    # ja existe no seed passado para a validacao.
    problemas = _validar([_meu_video(jogo="Repo", jogo_no_seed=False)])

    assert "nao esta no" not in _mensagens(problemas)


def test_jogo_reconhecido_por_alias_conta_como_no_seed():
    problemas = _validar([_meu_video(jogo="repo", jogo_no_seed=False)])

    assert "nao esta no" not in _mensagens(problemas)


def test_jogo_ausente_do_seed_e_reportado_mesmo_com_flag_dizendo_que_esta():
    problemas = _validar([_meu_video(jogo="Lava and Aqua", jogo_no_seed=True)])

    assert "nao esta no" in _mensagens(problemas)


# --- Video de referencia coletado antes das colunas descricao/tags existirem ---

def _validar_referencia(descricao="", tags=None):
    video = _video()
    video.descricao = descricao
    video.tags = tags or []
    return validar_dados(
        [video],
        [_jogo()],
        [_canal()],
        [_meu()],
        chave_configurada=True,
        canal_configurado=True,
    )


def test_video_de_referencia_sem_descricao_e_sem_tags_vira_aviso():
    problemas = _validar_referencia()

    assert "aviso" in _severidades(problemas)
    assert "sem descricao e sem tags" in _mensagens(problemas)
    assert "--forcar" in _sugestoes(problemas)


def test_video_de_referencia_com_descricao_nao_gera_o_aviso():
    problemas = _validar_referencia(descricao="nesse video eu trouxe Repo")

    assert "sem descricao e sem tags" not in _mensagens(problemas)


def test_video_de_referencia_so_com_tags_nao_gera_o_aviso():
    problemas = _validar_referencia(tags=["repo"])

    assert "sem descricao e sem tags" not in _mensagens(problemas)
