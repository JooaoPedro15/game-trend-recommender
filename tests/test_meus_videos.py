import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leitor_csv import _ler_linhas
from meus_videos import (
    CAMPOS_MEU_VIDEO,
    calcular_score_resultado_real,
    colunas_faltando,
    ler_meus_videos,
    listar_meus_videos_sem_jogo,
    migrar_meus_videos,
    salvar_meu_video,
    sugestao_deteccao,
)
from modelos import MeuVideo


def _meu_video(
    video_id="vid1",
    views=500000,
    likes=40000,
    comentarios=2000,
    status_analise="pendente",
) -> MeuVideo:
    return MeuVideo(
        video_id=video_id,
        titulo="Joguei o jogo de terror mais pesado do ano",
        url=f"https://www.youtube.com/watch?v={video_id}",
        data_publicacao="2026-06-10",
        jogo_detectado="Resident Evil",
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video="longo",
        status_analise=status_analise,
    )


def test_cria_csv_com_cabecalho_e_salva_video(tmp_path):
    caminho = tmp_path / "meus_videos.csv"

    resultado = salvar_meu_video(caminho, _meu_video(), data_coleta="2026-06-17")

    assert resultado == "criado"
    linhas = _ler_linhas(caminho)
    assert len(linhas) == 1
    assert list(linhas[0].keys()) == CAMPOS_MEU_VIDEO
    assert linhas[0]["video_id"] == "vid1"
    assert linhas[0]["data_coleta"] == "2026-06-17"
    assert linhas[0]["jogo_detectado"] == "Resident Evil"


def test_atualiza_video_existente_sem_duplicar(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(views=100000), data_coleta="2026-06-15")

    resultado = salvar_meu_video(
        caminho,
        _meu_video(views=900000, likes=80000, comentarios=5000),
        data_coleta="2026-06-17",
    )

    assert resultado == "atualizado"
    linhas = _ler_linhas(caminho)
    assert len(linhas) == 1
    assert linhas[0]["views"] == "900000"
    assert linhas[0]["likes"] == "80000"
    assert linhas[0]["comentarios"] == "5000"
    assert linhas[0]["data_coleta"] == "2026-06-17"


def test_update_preserva_status_analise(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(status_analise="analisado"), data_coleta="2026-06-15")

    # Recoletar manda status "pendente", mas o ja registrado deve ser preservado.
    salvar_meu_video(caminho, _meu_video(views=999, status_analise="pendente"), data_coleta="2026-06-17")

    linhas = _ler_linhas(caminho)
    assert linhas[0]["status_analise"] == "analisado"


def test_score_resultado_real_reflete_metricas(tmp_path):
    fraco = calcular_score_resultado_real(_meu_video(views=1000, likes=10, comentarios=1))
    forte = calcular_score_resultado_real(
        _meu_video(views=2000000, likes=200000, comentarios=10000)
    )

    assert 0 <= fraco < forte <= 100


def test_score_salvo_no_csv(tmp_path):
    caminho = tmp_path / "meus_videos.csv"

    salvar_meu_video(caminho, _meu_video(), data_coleta="2026-06-17")

    linhas = _ler_linhas(caminho)
    assert float(linhas[0]["score_resultado_real"]) > 0


def _sem_jogo(video_id, views) -> MeuVideo:
    return MeuVideo(
        video_id=video_id,
        titulo=f"video misterioso {video_id}",
        url=f"https://www.youtube.com/watch?v={video_id}",
        data_publicacao="2026-06-10",
        jogo_detectado="",
        confianca_jogo="nao_detectado",
        fonte_deteccao="nao_detectado",
        views=views,
        likes=10,
        comentarios=1,
        tipo_video="curto",
    )


def test_listar_meus_videos_sem_jogo_filtra_e_ordena(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(video_id="comjogo", views=100))  # tem jogo detectado
    salvar_meu_video(caminho, _sem_jogo("sem1", views=300))
    salvar_meu_video(caminho, _sem_jogo("sem2", views=900))

    sem = listar_meus_videos_sem_jogo(caminho)

    assert [video.video_id for video in sem] == ["sem2", "sem1"]
    assert all(video.jogo_detectado == "" for video in sem)


def test_listar_meus_videos_sem_jogo_csv_inexistente(tmp_path):
    assert listar_meus_videos_sem_jogo(tmp_path / "nao_existe.csv") == []


def test_sugestao_deteccao_com_e_sem_marcador():
    assert "alias" in sugestao_deteccao("Jogo: Algum Misterio")
    assert "Jogo: Nome" in sugestao_deteccao("ISSO me assustou demais")


def test_ler_csv_antigo_sem_novas_colunas_usa_defaults(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    caminho.write_text(
        "\n".join(
            [
                "video_id,data_coleta,data_publicacao,titulo,jogo_detectado,confianca_jogo,fonte_deteccao,url,views,likes,comentarios,tipo_video,score_resultado_real,status_analise",
                "vid antigo,2026-06-17,2026-06-10,Titulo antigo,,nao_detectado,nao_detectado,https://y/vid,10,1,0,curto,1.0,pendente",
            ]
        ),
        encoding="utf-8",
    )

    video = listar_meus_videos_sem_jogo(caminho)[0]

    assert video.descricao == ""
    assert video.tags == []
    assert video.duracao_segundos == 0
    assert video.motivo_nao_detectado == ""
    assert video.jogo_no_seed is True
    assert video.comentarios_incompletos is False


# --- Migracao do schema antigo do CSV ---
#
# Regressao: o arquivo nasceu com 14 colunas e o codigo passou a gravar 22. Como o
# csv.DictReader nao devolve a chave de uma coluna ausente, os leitores caiam no padrao
# ("" / 0) sem avisar — "nao coletado" ficava indistinguivel de "nao existe".

CABECALHO_ANTIGO = [
    "video_id",
    "data_coleta",
    "data_publicacao",
    "titulo",
    "jogo_detectado",
    "confianca_jogo",
    "fonte_deteccao",
    "url",
    "views",
    "likes",
    "comentarios",
    "tipo_video",
    "score_resultado_real",
    "status_analise",
]


def _csv_antigo(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CABECALHO_ANTIGO)
        escritor.writeheader()
        escritor.writerow(
            {
                "video_id": "VID1",
                "data_coleta": "2026-06-17",
                "data_publicacao": "2026-06-15",
                "titulo": "Um titulo antigo",
                "jogo_detectado": "Lethal Company",
                "confianca_jogo": "media",
                "fonte_deteccao": "titulo",
                "url": "https://y/VID1",
                "views": "1500",
                "likes": "50",
                "comentarios": "3",
                "tipo_video": "curto",
                "score_resultado_real": "20.6",
                "status_analise": "pendente",
            }
        )
    return caminho


def test_colunas_faltando_aponta_o_schema_antigo(tmp_path):
    faltando = colunas_faltando(_csv_antigo(tmp_path))

    assert "descricao" in faltando
    assert "tags" in faltando
    assert "motivo_nao_detectado" in faltando
    assert "video_id" not in faltando


def test_colunas_faltando_vazio_em_arquivo_atual(tmp_path):
    caminho = tmp_path / "novo.csv"
    salvar_meu_video(caminho, _meu_video("VID1"))

    assert colunas_faltando(caminho) == []


def test_colunas_faltando_vazio_quando_arquivo_nao_existe(tmp_path):
    assert colunas_faltando(tmp_path / "nao_existe.csv") == []


def test_migrar_acrescenta_colunas_e_preserva_dados(tmp_path):
    caminho = _csv_antigo(tmp_path)

    novas = migrar_meus_videos(caminho)

    assert "descricao" in novas
    assert colunas_faltando(caminho) == []

    videos = ler_meus_videos(caminho)
    assert len(videos) == 1
    assert videos[0].video_id == "VID1"
    assert videos[0].titulo == "Um titulo antigo"
    assert videos[0].jogo_detectado == "Lethal Company"
    assert videos[0].views == 1500
    assert videos[0].tipo_video == "curto"
    # colunas novas ficam vazias: a migracao nao inventa dado que so a API tem
    assert videos[0].descricao == ""
    assert videos[0].tags == []
    assert videos[0].duracao_segundos == 0


def test_migrar_e_idempotente(tmp_path):
    caminho = _csv_antigo(tmp_path)

    assert migrar_meus_videos(caminho) != []
    assert migrar_meus_videos(caminho) == []


def test_migrar_arquivo_inexistente_nao_cria_nada(tmp_path):
    caminho = tmp_path / "nao_existe.csv"

    assert migrar_meus_videos(caminho) == []
    assert not caminho.exists()


# --- status_analise: preservar decisao, nao preservar o valor inicial ---
#
# "pendente" e so o padrao do dataclass, nao uma escolha de ninguem. Deixar ele vencer na
# atualizacao congelava a linha: um video recoletado que passasse a ter jogo fora do seed
# nunca conseguia virar "jogo_pendente_seed". Status diferente do padrao continua vencendo.

def test_update_promove_status_a_partir_de_pendente(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    salvar_meu_video(caminho, _meu_video(status_analise="pendente"), data_coleta="2026-06-15")

    salvar_meu_video(
        caminho, _meu_video(status_analise="jogo_pendente_seed"), data_coleta="2026-06-17"
    )

    linhas = _ler_linhas(caminho)
    assert linhas[0]["status_analise"] == "jogo_pendente_seed"
