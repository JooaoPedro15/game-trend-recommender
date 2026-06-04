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
