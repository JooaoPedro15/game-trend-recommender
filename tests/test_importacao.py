import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cadastro_video import CAMPOS_VIDEO, importar_videos_csv
from leitor_csv import ler_videos_coletados


# Escreve um CSV de videos a partir de uma lista de dicionarios.
def _escrever_csv(caminho, linhas):
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(linha)


# Cria uma linha de video de teste com valores padrao sobrescreviveis.
def _linha(titulo="Jogo", url="https://exemplo.com/1", views="100"):
    return {
        "titulo": titulo,
        "canal": "Canal Teste",
        "plataforma": "youtube",
        "url": url,
        "views": views,
        "likes": "10",
        "comentarios": "1",
        "data_publicacao": "2026-05-01",
        "texto_comentarios": "",
    }


# Importa validos, ignora duplicado por URL e linha invalida; confere contagens e o que foi salvo.
def test_importa_validos_ignora_duplicado_e_invalido(tmp_path):
    origem = tmp_path / "novos.csv"
    destino = tmp_path / "videos_coletados.csv"
    _escrever_csv(
        origem,
        [
            _linha(titulo="Repo", url="https://exemplo.com/1"),
            _linha(titulo="Minecraft", url="https://exemplo.com/2"),
            _linha(titulo="Repo de novo", url="https://exemplo.com/1"),
            _linha(titulo="", url="https://exemplo.com/3"),
        ],
    )

    importados, duplicados, invalidos = importar_videos_csv(origem, destino)

    assert (importados, duplicados, invalidos) == (2, 1, 1)
    assert [video.titulo for video in ler_videos_coletados(destino)] == ["Repo", "Minecraft"]


# Linha com campo numerico invalido (views nao inteiro) conta como invalida.
def test_importa_conta_int_invalido_como_invalido(tmp_path):
    origem = tmp_path / "novos.csv"
    destino = tmp_path / "videos_coletados.csv"
    _escrever_csv(
        origem,
        [
            _linha(titulo="Valido", url="https://exemplo.com/1"),
            _linha(titulo="ViewsRuim", url="https://exemplo.com/2", views="abc"),
        ],
    )

    importados, duplicados, invalidos = importar_videos_csv(origem, destino)

    assert (importados, duplicados, invalidos) == (1, 0, 1)
    assert [video.titulo for video in ler_videos_coletados(destino)] == ["Valido"]


# Duplicado e detectado tambem contra videos que ja existem no destino.
def test_importa_detecta_duplicado_contra_destino_existente(tmp_path):
    origem = tmp_path / "novos.csv"
    destino = tmp_path / "videos_coletados.csv"
    _escrever_csv(destino, [_linha(titulo="Ja existe", url="https://exemplo.com/1")])
    _escrever_csv(
        origem,
        [
            _linha(titulo="Repetido", url="https://exemplo.com/1"),
            _linha(titulo="Novo", url="https://exemplo.com/2"),
        ],
    )

    importados, duplicados, invalidos = importar_videos_csv(origem, destino)

    assert (importados, duplicados, invalidos) == (1, 1, 0)
    assert [video.titulo for video in ler_videos_coletados(destino)] == ["Ja existe", "Novo"]


# --- Migracao de cabecalho do videos_coletados.csv ---
#
# O DictReader nao devolve a chave de uma coluna ausente, entao o leitor cai no padrao e
# "coletado antes da coluna existir" fica igual a "nao tem descricao". A migracao devolve a
# capacidade de distinguir os dois casos; ela nao inventa dado nenhum.

def test_colunas_faltando_aponta_as_colunas_novas(tmp_path):
    from cadastro_video import colunas_faltando_videos

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n",
        encoding="utf-8",
    )

    assert colunas_faltando_videos(caminho) == ["descricao", "tags"]


def test_arquivo_em_dia_nao_reporta_coluna_faltando(tmp_path):
    from cadastro_video import CAMPOS_VIDEO, colunas_faltando_videos

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(",".join(CAMPOS_VIDEO) + "\n", encoding="utf-8")

    assert colunas_faltando_videos(caminho) == []


def test_migrar_preserva_as_linhas_e_deixa_as_colunas_novas_vazias(tmp_path):
    from cadastro_video import migrar_videos_coletados
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n"
        "MEU BARCO,Lozao,youtube,https://y/1,90362,100,10,2026-08-01,,youtube,longo\n",
        encoding="utf-8",
    )

    novas = migrar_videos_coletados(caminho)

    assert novas == ["descricao", "tags"]
    lido = ler_videos_coletados(caminho)[0]
    assert lido.titulo == "MEU BARCO"
    assert lido.views == 90362
    assert lido.descricao == ""


def test_migrar_arquivo_em_dia_nao_reescreve(tmp_path):
    from cadastro_video import CAMPOS_VIDEO, migrar_videos_coletados

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(",".join(CAMPOS_VIDEO) + "\n", encoding="utf-8")
    antes = caminho.read_text(encoding="utf-8")

    assert migrar_videos_coletados(caminho) == []
    assert caminho.read_text(encoding="utf-8") == antes


def test_migrar_arquivo_inexistente_nao_quebra(tmp_path):
    from cadastro_video import migrar_videos_coletados

    assert migrar_videos_coletados(tmp_path / "nao_existe.csv") == []
