import argparse
from datetime import date, datetime
from pathlib import Path

from cadastro_video import VideoDuplicadoError, adicionar_video_csv, importar_videos_csv
from cadastro_jogo import adicionar_alias_jogo
from coletor_youtube import CACHE_PADRAO, coletar_canal, coletar_video_por_id, coletar_videos_por_ids
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from modelos import VideoColetado
from ranker import calcular_ranking, filtrar_oportunidades
from relatorio import gerar_relatorio_csv, gerar_relatorio_markdown
from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia
from diagnostico_dados import (
    encontrar_videos_sem_jogo,
    gerar_diagnostico,
    imprimir_diagnostico,
    imprimir_videos_sem_jogo,
)
from historico_ranking import comparar_ultimas_execucoes, imprimir_comparacao, salvar_snapshot
from watchlist import adicionar_jogo, listar_jogos, remover_jogo



BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
HISTORICO_CSV = DATA_DIR / "historico_rankings.csv"
WATCHLIST_CSV = DATA_DIR / "watchlist_jogos.csv"
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
    origem = getattr(args, "origem", None)
    nome = getattr(args, "nome", None)
    alias = getattr(args, "alias", None)
    video_id = getattr(args, "video_id", None)
    arquivo_ids = getattr(args, "arquivo_ids", None)
    channel_id = getattr(args, "channel_id", None)
    limite = getattr(args, "limite", 5)
    jogo = getattr(args, "jogo", None)

    if comando == "ranking":
        mostrar_ranking(plataforma, top, desde)
        return 0

    if comando == "adicionar_video":
        adicionar_video_interativo()
        return 0
    
    if comando == "exportar_ranking":
        exportar_ranking(plataforma, top, desde, formato)
        return 0

    if comando == "importar_videos":
        importar_videos_interativo(origem)
        return 0

    if comando == "diagnosticar_dados":
        diagnosticar_dados_interativo()
        return 0

    if comando == "videos_sem_jogo":
        videos_sem_jogo_interativo()
        return 0

    if comando == "adicionar_alias":
        adicionar_alias_interativo(nome, alias)
        return 0

    if comando == "coletar_video_youtube":
        coletar_video_youtube_interativo(video_id)
        return 0

    if comando == "coletar_videos_youtube":
        coletar_videos_youtube_interativo(arquivo_ids)
        return 0

    if comando == "coletar_canal_youtube":
        coletar_canal_youtube_interativo(channel_id, limite)
        return 0

    if comando == "salvar_snapshot_ranking":
        salvar_snapshot_ranking_interativo(plataforma, top, desde)
        return 0

    if comando == "comparar_rankings":
        comparar_rankings_interativo()
        return 0

    if comando == "oportunidades":
        mostrar_oportunidades(plataforma, top, desde)
        return 0

    if comando == "adicionar_watchlist":
        adicionar_watchlist_interativo(jogo)
        return 0

    if comando == "listar_watchlist":
        listar_watchlist_interativo()
        return 0

    if comando == "remover_watchlist":
        remover_watchlist_interativo(jogo)
        return 0

    if comando == "ranking_watchlist":
        ranking_watchlist_interativo(plataforma, top, desde)
        return 0

    return 0


# Le os CSVs de dados e delega para _montar_ranking (separa I/O de disco da logica pura).
def _carregar_ranking(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
):
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(VIDEOS_CSV)
    return _montar_ranking(jogos, videos, canais, plataforma, top, desde)


# Aplica os filtros de plataforma e data e o limite Top N (se houver) e retorna o ranking.
def _montar_ranking(
    jogos,
    videos,
    canais,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
):
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
        print(f"Oportunidade: {resultado.score_oportunidade:.1f}")
        print(f"Videos encontrados: {resultado.videos_encontrados}")
        print(f"Canais diferentes: {resultado.canais_diferentes}")
        print(f"Motivo: {resultado.motivo}")
        print(f"Acao recomendada: {resultado.acao_recomendada}")
        print()
        print("Videos que influenciaram:")
        for video in resultado.videos:
            taxa_engajamento = calcular_taxa_engajamento(video) * 100
            views_por_dia = calcular_views_por_dia(video)
            print(
                f"- {video.canal} | {video.plataforma} | "
                f"{video.views} views | {video.likes} likes | "
                f"{video.comentarios} comentarios | "
                f"{taxa_engajamento:.1f}% engajamento | "
                f"{views_por_dia:.0f} views/dia | "
                f"{video.data_publicacao} | {video.titulo}"
            )
            print(f"  {video.url}")


# Importa videos em lote de um CSV externo e mostra o resumo da importacao.
def importar_videos_interativo(caminho_origem: str) -> None:
    origem = Path(caminho_origem)
    if not origem.exists():
        print(f"Arquivo nao encontrado: {origem}")
        return

    importados, duplicados, invalidos = importar_videos_csv(origem, VIDEOS_CSV)

    print("=== Importacao de Videos ===")
    print(f"Videos importados: {importados}")
    print(f"Duplicados ignorados: {duplicados}")
    print(f"Linhas invalidas: {invalidos}")


# Le os dados e mostra um diagnostico da qualidade dos videos coletados.
def diagnosticar_dados_interativo() -> None:
    videos = ler_videos_coletados(VIDEOS_CSV)
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    imprimir_diagnostico(gerar_diagnostico(videos, jogos))


# Le os dados e lista os videos que nao foram associados a nenhum jogo.
def videos_sem_jogo_interativo() -> None:
    videos = ler_videos_coletados(VIDEOS_CSV)
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    imprimir_videos_sem_jogo(encontrar_videos_sem_jogo(videos, jogos))


# Adiciona um alias a um jogo do jogos_seed.csv e informa o resultado.
def adicionar_alias_interativo(nome_jogo: str, alias: str) -> None:
    try:
        adicionado = adicionar_alias_jogo(DATA_DIR / "jogos_seed.csv", nome_jogo, alias)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    if adicionado:
        print(f"Alias '{alias}' adicionado ao jogo '{nome_jogo}'.")
    else:
        print(f"O jogo '{nome_jogo}' ja tinha o alias '{alias}'.")


# Busca um video do YouTube por id e salva no CSV principal, reusando adicionar_video_csv.
def coletar_video_youtube_interativo(video_id: str) -> None:
    try:
        video = coletar_video_por_id(video_id, CACHE_PADRAO)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    if video is None:
        print(f"Video nao encontrado no YouTube: {video_id}")
        return

    try:
        adicionar_video_csv(VIDEOS_CSV, video)
    except VideoDuplicadoError as erro:
        print(f"Erro: {erro}")
        return
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    print(f"Video coletado e salvo: {video.titulo}")


# Coleta varios videos do YouTube a partir de um arquivo de ids e mostra o resumo.
def coletar_videos_youtube_interativo(caminho_ids: str) -> None:
    if not Path(caminho_ids).exists():
        print(f"Arquivo nao encontrado: {caminho_ids}")
        return

    try:
        resumo = coletar_videos_por_ids(caminho_ids, VIDEOS_CSV)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Coleta em lote do YouTube ===")
    print(f"IDs lidos: {resumo['lidos']}")
    print(f"Videos encontrados: {resumo['encontrados']}")
    print(f"Videos salvos: {resumo['salvos']}")
    print(f"Duplicados ignorados: {resumo['duplicados']}")
    print(f"Erros: {resumo['erros']}")


# Coleta os videos recentes de um canal do YouTube e mostra o resumo.
def coletar_canal_youtube_interativo(channel_id: str, limite: int) -> None:
    try:
        resumo = coletar_canal(channel_id, VIDEOS_CSV, limite)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Coleta de Canal do YouTube ===")
    print(f"Videos recentes considerados: {resumo['lidos']}")
    print(f"Videos encontrados: {resumo['encontrados']}")
    print(f"Videos salvos: {resumo['salvos']}")
    print(f"Duplicados ignorados: {resumo['duplicados']}")
    print(f"Erros: {resumo['erros']}")


# Calcula o ranking (com os filtros atuais) e acrescenta um snapshot ao historico.
def salvar_snapshot_ranking_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    if not ranking:
        print("Nenhum jogo no ranking; snapshot nao foi salvo.")
        return

    salvos = salvar_snapshot(HISTORICO_CSV, ranking)
    print(f"Snapshot salvo em: {HISTORICO_CSV}")
    print(f"Jogos registrados: {salvos}")


# Mostra apenas os jogos do ranking que passam nos criterios de oportunidade prioritaria.
def mostrar_oportunidades(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    oportunidades = filtrar_oportunidades(ranking)

    print("=== Oportunidades Prioritarias ===")
    print()

    if not oportunidades:
        print("Nenhum jogo passou nos criterios de oportunidade no momento.")
        print("Criterios: oportunidade >= 70, score final >= 60, saturacao >= 55.")
        return

    for posicao, resultado in oportunidades:
        print(f"#{posicao} no ranking | {resultado.jogo.nome}")
        print(
            f"  Score final: {resultado.score_final:.1f} | "
            f"Oportunidade: {resultado.score_oportunidade:.1f} | "
            f"Saturacao: {resultado.score_saturacao:.1f}"
        )
        print(f"  Acao recomendada: {resultado.acao_recomendada}")
        print(f"  Motivo: {resultado.motivo}")
        print()


# Compara as duas ultimas execucoes salvas no historico de rankings.
def comparar_rankings_interativo() -> None:
    comparacao = comparar_ultimas_execucoes(HISTORICO_CSV)
    if comparacao is None:
        print(
            "Historico insuficiente para comparar: sao necessarias pelo menos duas "
            "execucoes de salvar_snapshot_ranking."
        )
        return

    imprimir_comparacao(comparacao)


# Adiciona um jogo a watchlist (lista pessoal de jogos a acompanhar de perto).
def adicionar_watchlist_interativo(nome_jogo: str) -> None:
    try:
        adicionado = adicionar_jogo(WATCHLIST_CSV, nome_jogo)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    if adicionado:
        print(f"'{nome_jogo}' adicionado a watchlist.")
    else:
        print(f"'{nome_jogo}' ja esta na watchlist.")


# Lista os jogos da watchlist, na ordem em que foram adicionados.
def listar_watchlist_interativo() -> None:
    jogos = listar_jogos(WATCHLIST_CSV)
    print("=== Watchlist ===")
    if not jogos:
        print("(vazia)")
        return
    for nome in jogos:
        print(f"- {nome}")


# Remove um jogo da watchlist (ignora maiusculas/minusculas).
def remover_watchlist_interativo(nome_jogo: str) -> None:
    if remover_jogo(WATCHLIST_CSV, nome_jogo):
        print(f"'{nome_jogo}' removido da watchlist.")
    else:
        print(f"'{nome_jogo}' nao estava na watchlist.")


# Cruza os nomes da watchlist com o ranking atual (match por nome, ignorando
# maiusculas). Devolve, na ordem da watchlist, tuplas (nome, posicao, resultado);
# posicao e resultado sao None quando o jogo nao esta no ranking.
def cruzar_watchlist_com_ranking(nomes, ranking):
    por_nome = {
        resultado.jogo.nome.casefold(): (posicao, resultado)
        for posicao, resultado in enumerate(ranking, start=1)
    }
    return [(nome, *por_nome.get(nome.casefold(), (None, None))) for nome in nomes]


# Mostra como cada jogo da watchlist esta performando no ranking atual.
def ranking_watchlist_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    nomes = listar_jogos(WATCHLIST_CSV)
    if not nomes:
        print("Watchlist vazia. Adicione jogos com adicionar_watchlist.")
        return

    ranking = _carregar_ranking(plataforma, top, desde)

    print("=== Watchlist no Ranking Atual ===")
    print()
    for nome, posicao, resultado in cruzar_watchlist_com_ranking(nomes, ranking):
        if resultado is None:
            print(f"- {nome}: NAO aparece no ranking atual")
            print()
            continue
        print(f"- {nome}: #{posicao} no ranking")
        print(
            f"  Score final: {resultado.score_final:.1f} | "
            f"Oportunidade: {resultado.score_oportunidade:.1f}"
        )
        print(f"  Acao recomendada: {resultado.acao_recomendada}")
        print(f"  Motivo: {resultado.motivo}")
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
            origem="manual",
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

    importar = subcomandos.add_parser(
        "importar_videos", help="Importa videos em lote de um CSV externo."
    )
    importar.add_argument("origem", help="Caminho do CSV externo a importar.")

    subcomandos.add_parser(
        "diagnosticar_dados", help="Analisa a qualidade dos videos coletados."
    )

    subcomandos.add_parser(
        "videos_sem_jogo", help="Lista videos sem nenhum jogo detectado."
    )

    alias_parser = subcomandos.add_parser(
        "adicionar_alias", help="Adiciona um alias a um jogo do jogos_seed.csv."
    )
    alias_parser.add_argument("nome", help="Nome do jogo (ignora maiusculas).")
    alias_parser.add_argument("alias", help="Alias a adicionar ao jogo.")

    coletar = subcomandos.add_parser(
        "coletar_video_youtube", help="Busca um video do YouTube por id e salva no CSV."
    )
    coletar.add_argument("video_id", help="ID do video do YouTube (ex: dQw4w9WgXcQ).")

    coletar_lote = subcomandos.add_parser(
        "coletar_videos_youtube",
        help="Coleta varios videos do YouTube a partir de um arquivo de ids.",
    )
    coletar_lote.add_argument("arquivo_ids", help="Arquivo texto com um video_id por linha.")

    canal = subcomandos.add_parser(
        "coletar_canal_youtube",
        help="Coleta os videos recentes de um canal do YouTube e salva no CSV.",
    )
    canal.add_argument("channel_id", help="ID do canal do YouTube (ex: UC...).")
    canal.add_argument(
        "--limite",
        type=_top_valido,
        default=5,
        help="Quantos videos recentes coletar (padrao: 5).",
    )

    snapshot = subcomandos.add_parser(
        "salvar_snapshot_ranking",
        help="Calcula o ranking e acrescenta um snapshot ao historico.",
    )
    _adicionar_filtros(snapshot)

    subcomandos.add_parser(
        "comparar_rankings",
        help="Compara as duas ultimas execucoes salvas no historico.",
    )

    oportunidades = subcomandos.add_parser(
        "oportunidades",
        help="Lista apenas os jogos com alto potencial de oportunidade.",
    )
    _adicionar_filtros(oportunidades)

    adicionar_wl = subcomandos.add_parser(
        "adicionar_watchlist", help="Adiciona um jogo a watchlist."
    )
    adicionar_wl.add_argument("jogo", help="Nome do jogo a acompanhar.")

    subcomandos.add_parser("listar_watchlist", help="Lista os jogos da watchlist.")

    remover_wl = subcomandos.add_parser(
        "remover_watchlist", help="Remove um jogo da watchlist."
    )
    remover_wl.add_argument("jogo", help="Nome do jogo a remover.")

    ranking_wl = subcomandos.add_parser(
        "ranking_watchlist",
        help="Mostra como os jogos da watchlist aparecem no ranking atual.",
    )
    _adicionar_filtros(ranking_wl)

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
