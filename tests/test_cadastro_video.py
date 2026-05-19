import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from leitor_csv import ler_videos_coletados
from modelos import VideoColetado


class TestCadastroVideo(unittest.TestCase):
    def test_impede_duplicacao_por_url(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "videos_coletados.csv"
            _criar_csv_videos(caminho)
            video = _video(url="https://exemplo.com/video1")
            adicionar_video_csv(caminho, video)

            with self.assertRaises(VideoDuplicadoError):
                adicionar_video_csv(caminho, _video(url="https://exemplo.com/video1"))

            videos = ler_videos_coletados(caminho)
            self.assertEqual(len(videos), 1)

    def test_adiciona_video_convertido_no_csv(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "videos_coletados.csv"
            _criar_csv_videos(caminho)
            video = _video(url="https://exemplo.com/video2")

            adicionar_video_csv(caminho, video)

            videos = ler_videos_coletados(caminho)
            self.assertEqual(videos[0].views, 800000)
            self.assertEqual(videos[0].likes, 90000)
            self.assertEqual(videos[0].comentarios, 1200)


def _criar_csv_videos(caminho: Path) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(
            [
                "titulo",
                "canal",
                "plataforma",
                "url",
                "views",
                "likes",
                "comentarios",
                "data_publicacao",
                "texto_comentarios",
            ]
        )


def _video(url: str) -> VideoColetado:
    return VideoColetado(
        titulo="Esse jogo de terror me quebrou",
        canal="Core",
        plataforma="youtube",
        url=url,
        views=800000,
        likes=90000,
        comentarios=1200,
        data_publicacao="2026-05-18",
        texto_comentarios="qual nome repo",
    )


if __name__ == "__main__":
    unittest.main()
