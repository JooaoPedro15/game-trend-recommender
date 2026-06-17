import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import MeuVideo
from relatorio_meu_canal import (
    desempenho_por_formato,
    desempenho_por_jogo,
    gerar_relatorio_meu_canal_markdown,
    melhores_videos,
)


# Data antiga zera recencia/velocidade do score: o resultado real fica deterministico
# (volume + engajamento), sem depender da data de hoje. forte ~66, medio ~51, fraco ~4.
def _meu(jogo, video_id, views, likes, comentarios, tipo="longo"):
    return MeuVideo(
        video_id=video_id,
        titulo=f"video {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="media" if jogo else "nao_detectado",
        fonte_deteccao="titulo" if jogo else "nao_detectado",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video=tipo,
    )


def _forte(jogo, video_id, tipo="longo"):
    return _meu(jogo, video_id, 900000, 120000, 8000, tipo)


def _fraco(jogo, video_id, tipo="longo"):
    return _meu(jogo, video_id, 80000, 200, 50, tipo)


def test_melhores_videos_ordena_e_limita():
    videos = [_fraco("RE", "ruim"), _forte("RE", "bom")]

    melhores = melhores_videos(videos, limite=1)

    assert len(melhores) == 1
    assert melhores[0].video.video_id == "bom"
    assert melhores[0].score >= 60.0


def test_desempenho_por_jogo_agrupa_e_ordena_por_melhor():
    videos = [_forte("RE", "a"), _fraco("RE", "b"), _fraco("LC", "c")]

    desempenhos = desempenho_por_jogo(videos)

    assert [d.jogo for d in desempenhos] == ["RE", "LC"]
    assert desempenhos[0].videos == 2
    assert desempenhos[0].melhor_score >= 60.0


def test_desempenho_por_jogo_ignora_sem_jogo():
    videos = [_forte("RE", "a"), _fraco("", "semjogo")]

    desempenhos = desempenho_por_jogo(videos)

    assert [d.jogo for d in desempenhos] == ["RE"]


def test_desempenho_por_formato_media_e_ordena():
    videos = [_forte("RE", "a", tipo="curto"), _fraco("LC", "b", tipo="longo")]

    desempenhos = desempenho_por_formato(videos)

    assert desempenhos[0].tipo_video == "curto"
    assert desempenhos[0].videos == 1
    assert desempenhos[0].media_score > desempenhos[1].media_score


def test_gera_relatorio_com_todas_as_secoes(tmp_path):
    caminho = tmp_path / "meu_canal.md"
    videos = [_forte("Resident Evil", "a", tipo="curto"), _fraco("", "semjogo")]

    gerar_relatorio_meu_canal_markdown(caminho, videos)

    texto = caminho.read_text(encoding="utf-8")
    assert "# Relatorio de Aprendizado do Meu Canal" in texto
    assert "## Melhores videos por resultado real" in texto
    assert "## Jogos que mais funcionaram" in texto
    assert "## Formatos que performaram melhor" in texto
    assert "## Videos sem jogo detectado" in texto
    assert "## Recomendacoes operacionais" in texto
    assert "https://youtu.be/a" in texto


def test_gera_relatorio_vazio(tmp_path):
    caminho = tmp_path / "vazio.md"

    gerar_relatorio_meu_canal_markdown(caminho, [])

    assert "Nenhum video coletado" in caminho.read_text(encoding="utf-8")
