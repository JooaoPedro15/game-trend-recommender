import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leitor_csv import ler_canais_referencia
from modelos import VideoColetado


# Garante que as colunas de nicho sao lidas quando existem no CSV.
def test_le_canais_com_colunas_de_nicho(tmp_path):
    caminho = tmp_path / "canais.csv"
    caminho.write_text(
        "nome,plataforma,url,peso,nicho,tipo_conteudo,peso_similaridade\n"
        "Canal A,youtube,https://y/a,1.0,gaming_humor,gameplay,1.3\n",
        encoding="utf-8",
    )

    canais = ler_canais_referencia(caminho)

    assert len(canais) == 1
    canal = canais[0]
    assert canal.nicho == "gaming_humor"
    assert canal.tipo_conteudo == "gameplay"
    assert canal.peso_similaridade == 1.3


# Garante compatibilidade com CSV antigo (sem as colunas novas): usa os valores padrao.
def test_le_canais_sem_colunas_de_nicho_usa_padroes(tmp_path):
    caminho = tmp_path / "canais_antigo.csv"
    caminho.write_text(
        "nome,plataforma,url,peso\n"
        "Canal Antigo,tiktok,https://t/a,1.2\n",
        encoding="utf-8",
    )

    canais = ler_canais_referencia(caminho)

    assert len(canais) == 1
    canal = canais[0]
    assert canal.nicho == "desconhecido"
    assert canal.tipo_conteudo == "desconhecido"
    assert canal.peso_similaridade == 1.0


# --- Descricao e tags no video de referencia ---
#
# A API devolve os dois na mesma resposta que ja traz titulo e metricas, e o coletor de
# referencia descartava ambos. E na descricao que o canal escreve o nome do jogo.

def test_video_coletado_tem_descricao_e_tags_vazias_por_padrao():
    video = VideoColetado(
        titulo="t",
        canal="c",
        plataforma="youtube",
        url="https://y/1",
        views=1,
        likes=1,
        comentarios=1,
        data_publicacao="2026-08-01",
        texto_comentarios="",
    )

    assert video.descricao == ""
    assert video.tags == []


def test_duas_instancias_nao_compartilham_a_lista_de_tags():
    primeiro = VideoColetado("t", "c", "youtube", "u", 1, 1, 1, "2026-08-01", "")
    segundo = VideoColetado("t", "c", "youtube", "u", 1, 1, 1, "2026-08-01", "")

    primeiro.tags.append("repo")

    assert segundo.tags == []


def test_gravar_e_reler_preserva_descricao_e_tags(tmp_path):
    from cadastro_video import adicionar_video_csv
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "videos_coletados.csv"
    video = VideoColetado(
        titulo="MEU BARCO NAUFRAGO",
        canal="Lozao",
        plataforma="youtube",
        url="https://y/RbIxXnNtwBg",
        views=90362,
        likes=100,
        comentarios=10,
        data_publicacao="2026-08-01",
        texto_comentarios="",
        descricao="nesse video eu trouxe How to fish um game de pescaria",
        tags=["pescaria", "how to fish"],
    )

    adicionar_video_csv(caminho, video)
    lido = ler_videos_coletados(caminho)[0]

    assert lido.descricao == "nesse video eu trouxe How to fish um game de pescaria"
    assert lido.tags == ["pescaria", "how to fish"]


def test_linha_sem_as_colunas_novas_le_como_vazio(tmp_path):
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "antigo.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n"
        "t,Canal,youtube,https://y/1,10,1,1,2026-08-01,,youtube,curto\n",
        encoding="utf-8",
    )

    lido = ler_videos_coletados(caminho)[0]

    assert lido.descricao == ""
    assert lido.tags == []
