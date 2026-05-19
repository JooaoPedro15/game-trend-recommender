from pathlib import Path

from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from ranker import calcular_ranking


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


def main() -> None:
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(DATA_DIR / "videos_coletados.csv")
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


if __name__ == "__main__":
    main()
