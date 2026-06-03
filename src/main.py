import sys
from datetime import date, datetime
from pathlib import Path

from cadastro_video import VideoDuplicadoError, adicionar_video_csv
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from modelos import VideoColetado
from ranker import calcular_ranking
from relatorio import gerar_relatorio_markdown
from metricas_video import calcular_taxa_engajamento



BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
REPORTS_DIR = BASE_DIR / "reports"
RANKING_REPORT = REPORTS_DIR / "ranking.md"


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    comando = argumentos[0] if argumentos else "ranking"
    plataforma = _ler_argumento(argumentos, "--plataforma")

    try:
        top = _ler_top(argumentos)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return 1

    if comando == "ranking":
        mostrar_ranking(plataforma, top)
        return 0

    if comando == "adicionar_video":
        adicionar_video_interativo()
        return 0
    
    if comando == "exportar_ranking":
        exportar_ranking(plataforma, top)
        return 0

    print(f"Comando desconhecido: {comando}")
    print("Use: python src/main.py [ranking|adicionar_video|exportar_ranking] [--plataforma NOME] [--top N]")
    return 1


# Le os dados, aplica o filtro de plataforma e o limite Top N (se houver) e retorna o ranking.
def _carregar_ranking(plataforma: str | None = None, top: int | None = None):
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(VIDEOS_CSV)
    if plataforma:
        videos = _filtrar_por_plataforma(videos, plataforma)
    ranking = calcular_ranking(jogos, videos, canais)
    if top is not None:
        ranking = ranking[:top]
    return ranking


def mostrar_ranking(plataforma: str | None = None, top: int | None = None) -> None:
    ranking = _carregar_ranking(plataforma, top)
    imprimir_ranking(ranking)

# Exporta o ranking atual para um arquivo Markdown com data e hora.
def exportar_ranking(plataforma: str | None = None, top: int | None = None) -> None:
    ranking = _carregar_ranking(plataforma, top)

    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
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


# Le o valor de um argumento simples no formato "--chave valor".
def _ler_argumento(argumentos: list[str], chave: str) -> str | None:
    if chave not in argumentos:
        return None
    indice = argumentos.index(chave)
    if indice + 1 < len(argumentos):
        return argumentos[indice + 1]
    return None


# Le e valida o argumento "--top N". Retorna None se ausente; levanta ValueError se invalido.
def _ler_top(argumentos: list[str]) -> int | None:
    valor = _ler_argumento(argumentos, "--top")
    if valor is None:
        return None
    erro = f"Valor invalido para --top: {valor}. Use um numero inteiro positivo."
    try:
        numero = int(valor)
    except ValueError:
        raise ValueError(erro)
    if numero <= 0:
        raise ValueError(erro)
    return numero


# Mantem apenas os videos da plataforma informada, ignorando maiusculas/minusculas.
def _filtrar_por_plataforma(
    videos: list[VideoColetado], plataforma: str
) -> list[VideoColetado]:
    plataforma_alvo = plataforma.casefold()
    return [video for video in videos if video.plataforma.casefold() == plataforma_alvo]


if __name__ == "__main__":
    raise SystemExit(main())
