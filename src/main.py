import sys
from datetime import date
from pathlib import Path

from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from modelos import VideoColetado
from ranker import calcular_ranking


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    comando = argumentos[0] if argumentos else "ranking"

    if comando == "ranking":
        mostrar_ranking()
        return 0

    if comando == "adicionar_video":
        adicionar_video_interativo()
        return 0

    print(f"Comando desconhecido: {comando}")
    print("Use: python src/main.py [ranking|adicionar_video]")
    return 1


def mostrar_ranking() -> None:
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(VIDEOS_CSV)
    ranking = calcular_ranking(jogos, videos, canais)

    imprimir_ranking(ranking)


def imprimir_ranking(ranking) -> None:
    print("=== Ranking de Games Recomendados ===")
    print()

    if not ranking:
        print("Nenhum jogo foi detectado nos videos coletados.")
        return

    for posicao, resultado in enumerate(ranking, start=1):
        print(f"{posicao}. {resultado.jogo.nome}")
        print(f"Score final: {resultado.score_final:.1f}")
        print(f"Tendencia: {resultado.score_tendencia:.1f}")
        print(f"Fit com o canal: {resultado.score_fit_canal:.1f}")
        print(f"Descoberta: {resultado.score_descoberta:.1f}")
        print(f"Saturacao: {resultado.score_saturacao:.1f}")
        print(f"Videos encontrados: {resultado.videos_encontrados}")
        print(f"Canais diferentes: {resultado.canais_diferentes}")
        print(f"Motivo: {resultado.motivo}")
        print()
        print("Videos que influenciaram:")
        for video in resultado.videos:
            print(
                f"- {video.canal} | {video.plataforma} | "
                f"{video.views} views | {video.titulo}"
            )
            print(f"  {video.url}")
        print()


def adicionar_video_interativo() -> None:
    print("=== Adicionar Video Manual ===")
    print()

    try:
        video = VideoColetado(
            titulo=_perguntar_obrigatorio("titulo"),
            canal=_perguntar_obrigatorio("canal"),
            plataforma=_perguntar_obrigatorio("plataforma"),
            url=_perguntar_obrigatorio("url"),
            views=_perguntar_int("views"),
            likes=_perguntar_int("likes"),
            comentarios=_perguntar_int("comentarios"),
            data_publicacao=_perguntar_data_publicacao(),
            texto_comentarios=input("texto_comentarios: ").strip(),
        )
        adicionar_video_csv(VIDEOS_CSV, video)
    except VideoDuplicadoError as erro:
        print(f"Erro: {erro}")
        return
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    print()
    print("Video cadastrado com sucesso.")


def _perguntar_obrigatorio(campo: str) -> str:
    while True:
        valor = input(f"{campo}: ").strip()
        if valor:
            return valor
        print(f"{campo} e obrigatorio.")


def _perguntar_int(campo: str) -> int:
    while True:
        valor = input(f"{campo}: ").strip()
        try:
            return int(valor)
        except ValueError:
            print(f"{campo} deve ser um numero inteiro.")


def _perguntar_data_publicacao() -> str:
    valor = input("data_publicacao: ").strip()
    if valor:
        return valor
    return date.today().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
