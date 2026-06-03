import argparse
from datetime import date, datetime
from pathlib import Path

from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from modelos import VideoColetado
from ranker import calcular_ranking
from relatorio import gerar_relatorio_csv, gerar_relatorio_markdown
from metricas_video import calcular_taxa_engajamento



BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
REPORTS_DIR = BASE_DIR / "reports"
RANKING_REPORT = REPORTS_DIR / "ranking.md"


def main(argv: list[str] | None = None) -> int:
    parser = _construir_parser()
    args = parser.parse_args(argv)

    comando = args.comando or "ranking"
    plataforma = getattr(args, "plataforma", None)
    top = getattr(args, "top", None)
    desde = getattr(args, "desde", None)
    formato = getattr(args, "formato", "md")

    if comando == "ranking":
        mostrar_ranking(plataforma, top, desde)
        return 0

    if comando == "adicionar_video":
        adicionar_video_interativo()
        return 0
    
    if comando == "exportar_ranking":
        exportar_ranking(plataforma, top, desde, formato)
        return 0

    return 0


# Le os dados, aplica os filtros de plataforma e data e o limite Top N (se houver) e retorna o ranking.
def _carregar_ranking(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
):
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(VIDEOS_CSV)
    if plataforma:
        videos = _filtrar_por_plataforma(videos, plataforma)
    if desde is not None:
        videos = _filtrar_por_data(videos, desde)
    ranking = calcular_ranking(jogos, videos, canais)
    if top is not None:
        ranking = ranking[:top]
    return ranking


def mostrar_ranking(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    imprimir_ranking(ranking)

# Exporta o ranking atual para um arquivo com data e hora, em Markdown (padrao) ou CSV.
def exportar_ranking(
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
    formato: str = "md",
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)

    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")

    if formato == "csv":
        caminho_relatorio = REPORTS_DIR / f"ranking_{data_hora}.csv"
        gerar_relatorio_csv(caminho_relatorio, ranking)
    else:
        caminho_relatorio = REPORTS_DIR / f"ranking_{data_hora}.md"
        gerar_relatorio_markdown(caminho_relatorio, ranking)

    print(f"Relatorio gerado em: {caminho_relatorio}")


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
          taxa_engajamento = calcular_taxa_engajamento(video) * 100

    print(
        f"- {video.canal} | {video.plataforma} | "
        f"{video.views} views | {video.likes} likes | "
        f"{video.comentarios} comentarios | "
        f"{taxa_engajamento:.1f}% engajamento | "
        f"{video.data_publicacao} | {video.titulo}"
    )
    print(f"  {video.url}")

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


# Valida o argumento --top: precisa ser um inteiro positivo.
def _top_valido(valor: str) -> int:
    try:
        numero = int(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"valor invalido para --top: {valor}")
    if numero <= 0:
        raise argparse.ArgumentTypeError(f"--top deve ser um inteiro positivo: {valor}")
    return numero


# Valida o argumento --desde: precisa estar no formato YYYY-MM-DD.
def _data_valida(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data invalida (use YYYY-MM-DD): {valor}")


# Adiciona os filtros comuns (--plataforma, --top, --desde) a um subcomando.
def _adicionar_filtros(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--plataforma",
        help="Filtra os videos por plataforma (ex: YouTube, TikTok). Ignora maiusculas.",
    )
    subparser.add_argument(
        "--top",
        type=_top_valido,
        help="Mostra apenas os N jogos com maior score.",
    )
    subparser.add_argument(
        "--desde",
        type=_data_valida,
        help="Considera apenas videos publicados nesta data ou depois (YYYY-MM-DD).",
    )


# Monta o parser de argumentos do CLI, com um subcomando para cada acao.
def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recomenda games com potencial para Shorts, Reels e TikTok.",
    )
    subcomandos = parser.add_subparsers(dest="comando")

    ranking = subcomandos.add_parser("ranking", help="Mostra o ranking no terminal.")
    _adicionar_filtros(ranking)

    exportar = subcomandos.add_parser(
        "exportar_ranking", help="Exporta o ranking para um arquivo Markdown."
    )
    _adicionar_filtros(exportar)
    exportar.add_argument(
        "--formato",
        choices=["md", "csv"],
        default="md",
        help="Formato do arquivo exportado: md ou csv (padrao: md).",
    )

    subcomandos.add_parser("adicionar_video", help="Cadastra um video manualmente.")

    return parser


# Mantem apenas os videos da plataforma informada, ignorando maiusculas/minusculas.
def _filtrar_por_plataforma(
    videos: list[VideoColetado], plataforma: str
) -> list[VideoColetado]:
    plataforma_alvo = plataforma.casefold()
    return [video for video in videos if video.plataforma.casefold() == plataforma_alvo]


# Mantem apenas os videos publicados em "desde" ou depois. Ignora videos com data invalida.
def _filtrar_por_data(
    videos: list[VideoColetado], desde: date
) -> list[VideoColetado]:
    selecionados = []
    for video in videos:
        try:
            data_video = date.fromisoformat(video.data_publicacao)
        except ValueError:
            continue
        if data_video >= desde:
            selecionados.append(video)
    return selecionados


if __name__ == "__main__":
    raise SystemExit(main())
