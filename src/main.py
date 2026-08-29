import argparse
from datetime import date, datetime
from pathlib import Path

from cadastro_video import VideoDuplicadoError, adicionar_video_csv, importar_videos_csv
from cadastro_jogo import adicionar_alias_jogo, adicionar_jogo_seed
from coletor_youtube import (
    CACHE_PADRAO,
    coletar_canal,
    coletar_detalhe_video,
    coletar_textos_comentarios,
    coletar_video_por_id,
    coletar_videos_por_ids,
    listar_videos_recentes_do_canal,
)
from analise_meu_canal import analisar_canal_completo, analisar_meu_canal
from comparacao_meu_canal import (
    comparar_recomendacoes_com_meu_canal,
    imprimir_comparacao_meu_canal,
)
from config import (
    ler_chave_youtube,
    ler_id_canal_proprio,
    obter_meu_canal_youtube_id,
    obter_youtube_api_key,
)
from meus_videos import (
    colunas_faltando,
    imprimir_meus_videos_sem_jogo,
    ler_meus_videos,
    listar_meus_videos_sem_jogo,
    migrar_meus_videos,
)
from redeteccao import aplicar_redeteccao, imprimir_redeteccao
from relatorio_meu_canal import gerar_relatorio_meu_canal_markdown
from repetir_jogos import imprimir_jogos_para_repetir, jogos_para_repetir
from jogos_falhos import imprimir_jogos_que_nao_funcionaram, jogos_que_nao_funcionaram
from relatorio_calibracao import gerar_relatorio_calibracao_markdown
from status_sistema import coletar_status, imprimir_status
from relatorio_diario import gerar_relatorio_diario_markdown
from validacao_dados import imprimir_validacao, validar_dados
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from modelos import ComentariosColetados, VideoColetado
from ranker import calcular_ranking, filtrar_oportunidades
from relatorio import (
    gerar_relatorio_csv,
    gerar_relatorio_evidencias_markdown,
    gerar_relatorio_markdown,
)
from metricas_video import calcular_taxa_engajamento, calcular_views_por_dia
from diagnostico_dados import (
    encontrar_videos_sem_jogo,
    gerar_diagnostico,
    imprimir_diagnostico,
    imprimir_videos_sem_jogo,
)
from historico_ranking import comparar_ultimas_execucoes, imprimir_comparacao, salvar_snapshot
from watchlist import adicionar_jogo, listar_jogos, remover_jogo
from evidencias_jogo import (
    calcular_score_evidencia_criadores,
    gerar_evidencias,
    resumir_evidencia_criadores,
)
from detector_jogo import detectar_jogo_em_conteudo



BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
MEUS_VIDEOS_CSV = DATA_DIR / "meus_videos.csv"
MEU_CANAL_IDS_CHECKPOINT = DATA_DIR / "meu_canal_ids_checkpoint.json"
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
    aliases = getattr(args, "aliases", "")
    genero = getattr(args, "genero", "")
    fit = getattr(args, "fit", 5.0)
    video_id = getattr(args, "video_id", None)
    arquivo_ids = getattr(args, "arquivo_ids", None)
    channel_id = getattr(args, "channel_id", None)
    limite = getattr(args, "limite", 5)
    jogo = getattr(args, "jogo", None)
    tipo = getattr(args, "tipo", None)
    comentarios = getattr(args, "comentarios", 20)
    dry_run = getattr(args, "dry_run", False)
    todos_videos = getattr(args, "todos_videos", False)
    comentarios_extra_sem_jogo = getattr(args, "comentarios_extra_sem_jogo", 0)
    todos_comentarios = getattr(args, "todos_comentarios", False)
    forcar = getattr(args, "forcar", False)

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

    if comando == "adicionar_jogo":
        adicionar_jogo_interativo(nome, aliases, genero, fit)
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

    if comando == "listar_meus_videos_youtube":
        listar_meus_videos_youtube_interativo(limite)
        return 0

    if comando == "coletar_meu_canal":
        coletar_meu_canal_interativo(
            limite,
            comentarios,
            dry_run,
            todos_videos,
            comentarios_extra_sem_jogo,
            todos_comentarios,
            forcar,
        )
        return 0

    if comando == "meus_videos_sem_jogo":
        meus_videos_sem_jogo_interativo()
        return 0

    if comando == "redetectar_meus_videos":
        redetectar_meus_videos_interativo(dry_run)
        return 0

    if comando == "diagnosticar_meu_video":
        diagnosticar_meu_video_interativo(video_id)
        return 0

    if comando == "comparar_recomendacoes_meu_canal":
        comparar_recomendacoes_meu_canal_interativo(plataforma, top, desde)
        return 0

    if comando == "relatorio_meu_canal":
        relatorio_meu_canal_interativo()
        return 0

    if comando == "jogos_para_repetir":
        jogos_para_repetir_interativo(plataforma, top, desde)
        return 0

    if comando == "jogos_que_nao_funcionaram":
        jogos_que_nao_funcionaram_interativo(plataforma, top, desde)
        return 0

    if comando == "relatorio_calibracao":
        relatorio_calibracao_interativo()
        return 0

    if comando == "status_sistema":
        status_sistema_interativo()
        return 0

    if comando == "validar_dados":
        validar_dados_interativo()
        return 0

    if comando == "rotina_diaria":
        rotina_diaria_interativo(limite, comentarios, top, plataforma, desde, dry_run)
        return 0

    if comando == "relatorio_diario":
        relatorio_diario_interativo(plataforma, top, desde)
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

    if comando == "evidencias_jogo":
        evidencias_jogo_interativo(jogo, tipo)
        return 0

    if comando == "exportar_evidencias_jogos":
        exportar_evidencias_jogos(plataforma, top, desde)
        return 0

    return 0


# Le os CSVs de dados e delega para _montar_ranking (separa I/O de disco da logica pura).
# Inclui os meus videos (se houver) para o ranking considerar o fit real do canal.
def _carregar_ranking(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
):
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    videos = ler_videos_coletados(VIDEOS_CSV)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    return _montar_ranking(jogos, videos, canais, plataforma, top, desde, meus_videos)


# Aplica os filtros de plataforma e data e o limite Top N (se houver) e retorna o ranking.
# Os filtros incidem so nos videos de referencia; o fit real usa todo o meu historico.
def _montar_ranking(
    jogos,
    videos,
    canais,
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
    meus_videos=None,
):
    if plataforma:
        videos = _filtrar_por_plataforma(videos, plataforma)
    if desde is not None:
        videos = _filtrar_por_data(videos, desde)
    ranking = calcular_ranking(jogos, videos, canais, meus_videos)
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


# Exporta para Markdown, com data e hora, os jogos e os videos/criadores que servem de evidencia.
def exportar_evidencias_jogos(
    plataforma: str | None = None,
    top: int | None = None,
    desde: date | None = None,
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")

    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    caminho_relatorio = REPORTS_DIR / f"evidencias_jogos_{data_hora}.md"
    gerar_relatorio_evidencias_markdown(caminho_relatorio, ranking, canais)

    print(f"Relatorio gerado em: {caminho_relatorio}")


# Formata o fit real para exibicao: "n/d" quando o jogo nunca apareceu no meu canal.
def _formatar_fit_real(score_fit_real: float | None) -> str:
    return "n/d" if score_fit_real is None else f"{score_fit_real:.1f}"


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
        print(f"Fit real (meu canal): {_formatar_fit_real(resultado.score_fit_real)}")
        print(f"Formato sugerido: {resultado.formato_sugerido or 'n/d'}")
        print(f"Descoberta: {resultado.score_descoberta:.1f}")
        print(f"Saturacao: {resultado.score_saturacao:.1f}")
        print(f"Oportunidade: {resultado.score_oportunidade:.1f}")
        print(f"Evidencia criadores: {resultado.score_evidencia_criadores:.1f}")
        print(f"Evidencia no meu nicho: {resultado.score_evidencia_nicho:.1f}")
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


# Cadastra um jogo novo no jogos_seed.csv e informa o resultado. Os aliases chegam da CLI
# no mesmo formato do arquivo (separados por |), para quem edita o CSV na mao e quem usa o
# comando escreverem a mesma coisa.
def adicionar_jogo_interativo(
    nome_jogo: str, aliases: str, genero: str, fit_inicial: float
) -> None:
    lista_aliases = [alias.strip() for alias in (aliases or "").split("|") if alias.strip()]
    try:
        adicionar_jogo_seed(
            DATA_DIR / "jogos_seed.csv", nome_jogo, lista_aliases, genero, fit_inicial
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    print(f"Jogo '{nome_jogo}' cadastrado no jogos_seed.csv (fit inicial {fit_inicial}).")
    print(
        "A deteccao passa a reconhecer esse jogo nos videos de referencia e nos seus. "
        "Rode validar_dados para conferir."
    )


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


# Lista os IDs (e titulos) dos meus videos recentes do YouTube, sem salvar no CSV.
# Usa o canal proprio (MEU_CANAL_YOUTUBE_ID); avisa de forma clara se nao estiver definido.
def listar_meus_videos_youtube_interativo(limite: int) -> None:
    channel_id = ler_id_canal_proprio()
    if channel_id is None:
        print(
            "MEU_CANAL_YOUTUBE_ID nao definido no ambiente. "
            "Defina a variavel antes de listar os seus videos (veja .env.example)."
        )
        return

    try:
        videos = listar_videos_recentes_do_canal(channel_id, limite)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Meus Videos Recentes do YouTube ===")
    if not videos:
        print("Nenhum video encontrado para o canal.")
        return

    for posicao, video in enumerate(videos, start=1):
        print(f"{posicao}. {video['video_id']} | {video['titulo']}")


# Mostra o plano da coleta do canal (sem chamar a API nem salvar), com o custo de quota.
# Usado pelo modo dry-run do coletar_meu_canal e da rotina_diaria.
def _plano_coleta_meu_canal(limite: int, limite_comentarios: int) -> None:
    channel_id = ler_id_canal_proprio()
    alvo = channel_id or "(MEU_CANAL_YOUTUBE_ID nao configurado)"
    quota = 2 + 2 * limite
    print(
        f"DRY-RUN: coletaria ate {limite} videos recentes do canal {alvo}, detectaria o jogo "
        f"de cada um e salvaria/atualizaria {MEUS_VIDEOS_CSV}."
    )
    print(
        f"DRY-RUN: comentarios so para videos NAO detectados por titulo/descricao/tags "
        f"(ate {limite_comentarios}/video)."
    )
    print(
        f"DRY-RUN: custo estimado de quota: ate {quota} unidades (pior caso, todos sem "
        "deteccao por metadado). Nenhuma chamada de API feita."
    )


# Mostra o plano da coleta COMPLETA (--todos-videos), sem chamar a API nem salvar.
def _plano_coleta_completa(
    limite_maximo: int | None,
    limite_comentarios: int,
    comentarios_extra_sem_jogo: int,
    forcar: bool = False,
) -> None:
    channel_id = ler_id_canal_proprio()
    alvo = channel_id or "(MEU_CANAL_YOUTUBE_ID nao configurado)"
    teto = "sem teto" if limite_maximo is None else f"ate {limite_maximo} videos"
    print(
        f"DRY-RUN: coletaria TODOS os videos do canal {alvo} ({teto}), paginando a uploads "
        "playlist; detalhes em lote (videos.list, ~1 unidade por 50 videos)."
    )
    extra = (
        f", e {comentarios_extra_sem_jogo} extra so nos que continuarem sem jogo"
        if comentarios_extra_sem_jogo > limite_comentarios
        else ""
    )
    print(
        f"DRY-RUN: comentarios so para videos NAO detectados por titulo/descricao/tags "
        f"(ate {limite_comentarios}/video{extra})."
    )
    if forcar:
        print(
            "DRY-RUN: --forcar ligado: reanalisaria TAMBEM os videos ja salvos em "
            "meus_videos.csv (nenhum e pulado por cache), recoletando descricao, tags e "
            "metricas. Nada foi salvo."
        )
    else:
        print("DRY-RUN: videos ja em meus_videos.csv sao pulados (cache). Nada foi salvo.")


# Coleta e analisa os meus videos e salva em data/meus_videos.csv. Sem --todos-videos pega
# so os recentes (limite, padrao 5); com --todos-videos pega o canal inteiro de forma
# incremental e economica. Checa chave e canal antes de tocar a API. Com dry_run, so o plano.
def coletar_meu_canal_interativo(
    limite: int | None,
    limite_comentarios: int,
    dry_run: bool = False,
    todos_videos: bool = False,
    comentarios_extra_sem_jogo: int = 0,
    todos_comentarios: bool = False,
    forcar: bool = False,
) -> None:
    # Sem --todos-videos a coleta ja reanalisa todos os videos que busca, entao --forcar
    # nao teria efeito nenhum: avisar e melhor do que aceitar em silencio uma flag inerte.
    if forcar and not todos_videos:
        print(
            "AVISO: --forcar so vale com --todos-videos (a coleta recente ja reanalisa "
            "os videos que busca) e foi ignorado."
        )
        forcar = False

    if todos_comentarios:
        print(
            "AVISO: --todos-comentarios ainda nao e recomendado (gasto de quota alto) e "
            "foi ignorado; a coleta usa comentarios so onde o jogo nao foi detectado."
        )

    if dry_run:
        if todos_videos:
            _plano_coleta_completa(
                limite, limite_comentarios, comentarios_extra_sem_jogo, forcar
            )
        else:
            _plano_coleta_meu_canal(limite if limite is not None else 5, limite_comentarios)
        print("DRY-RUN: nada foi salvo.")
        return

    if ler_chave_youtube() is None:
        print(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de coletar do YouTube (veja .env.example)."
        )
        return

    channel_id = ler_id_canal_proprio()
    if channel_id is None:
        print(
            "MEU_CANAL_YOUTUBE_ID nao definido no ambiente. "
            "Defina a variavel antes de analisar o seu canal (veja .env.example)."
        )
        return

    _migrar_meus_videos_se_preciso()
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")

    if todos_videos:
        _coletar_meu_canal_completo(
            channel_id, jogos, limite, limite_comentarios, comentarios_extra_sem_jogo, forcar
        )
        return

    try:
        resumo = analisar_meu_canal(
            channel_id,
            jogos,
            MEUS_VIDEOS_CSV,
            limite if limite is not None else 5,
            limite_comentarios,
            comentarios_extra_sem_jogo,
        )
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Analise do Meu Canal ===")
    print(f"Videos analisados: {resumo['analisados']}")
    print(f"Jogos detectados: {resumo['jogos_detectados']}")
    print(f"Jogos nao detectados: {resumo['jogos_nao_detectados']}")
    print(f"Videos novos: {resumo['novos']}")
    print(f"Videos atualizados: {resumo['atualizados']}")
    print(f"Erros: {resumo['erros']}")


# Atualiza o cabecalho do meus_videos.csv quando ele veio de uma versao antiga do projeto,
# antes de coletar. Fica em silencio quando o arquivo ja esta em dia. Roda aqui, e nao no
# salvar_meu_video, para acontecer UMA vez por coleta (e nao uma vez por video) e para o
# usuario ver que o arquivo mudou de formato.
def _migrar_meus_videos_se_preciso() -> None:
    novas_colunas = migrar_meus_videos(MEUS_VIDEOS_CSV)
    if novas_colunas:
        print(
            f"Formato do meus_videos.csv atualizado: {len(novas_colunas)} coluna(s) nova(s) "
            f"({', '.join(novas_colunas)}). Os dados antigos foram preservados."
        )


# Roda a coleta completa (--todos-videos) e mostra o progresso. limite (se dado) e o teto.
def _coletar_meu_canal_completo(
    channel_id: str,
    jogos,
    limite_maximo: int | None,
    limite_comentarios: int,
    comentarios_extra_sem_jogo: int,
    forcar: bool = False,
) -> None:
    ids_existentes = {video.video_id for video in ler_meus_videos(MEUS_VIDEOS_CSV)}
    try:
        resumo = analisar_canal_completo(
            channel_id,
            jogos,
            MEUS_VIDEOS_CSV,
            ids_existentes,
            limite_maximo,
            limite_comentarios,
            comentarios_extra_sem_jogo,
            forcar,
            caminho_checkpoint=MEU_CANAL_IDS_CHECKPOINT,
            ao_progresso_ids=_imprimir_progresso_ids,
            ao_progresso_lote=_imprimir_progresso_lote,
        )
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Coleta Completa do Meu Canal ===")
    print(f"Videos encontrados: {resumo['encontrados']}")
    print(f"Ja em cache (pulados): {resumo['em_cache']}")
    print(f"Videos analisados: {resumo['analisados']}")
    print(f"Jogos detectados sem comentarios: {resumo['detectados_sem_comentarios']}")
    print(f"Jogos detectados por comentarios: {resumo['detectados_por_comentarios']}")
    print(f"Videos ainda sem jogo: {resumo['sem_jogo']}")
    print(f"Erros: {resumo['erros']}")


# Mostra progresso da fase de listagem da playlist de uploads.
def _imprimir_progresso_ids(pagina: int, total_ids: int) -> None:
    print(f"Pagina de IDs {pagina}: {total_ids} video_ids acumulados.")


# Mostra progresso da fase de detalhes/deteccao ja com salvamento parcial.
def _imprimir_progresso_lote(lote: int, total_analisados: int) -> None:
    print(f"Lote {lote} processado: {total_analisados} videos analisados.")


# Recalcula a deteccao de todos os meus videos ja salvos, sem tocar a rede. Serve depois de
# cadastrar jogos/aliases ou de corrigir a deteccao: o texto necessario ja esta no CSV, entao
# nao ha motivo para pagar uma nova coleta so para reprocessa-lo.
def redetectar_meus_videos_interativo(dry_run: bool = False) -> None:
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    resumo, mudancas = aplicar_redeteccao(MEUS_VIDEOS_CSV, jogos, simular=dry_run)
    imprimir_redeteccao(resumo, mudancas)
    if dry_run:
        print()
        print("DRY-RUN: nada foi salvo.")


# Lista os meus videos em que nenhum jogo foi detectado, lendo data/meus_videos.csv.
def meus_videos_sem_jogo_interativo() -> None:
    imprimir_meus_videos_sem_jogo(listar_meus_videos_sem_jogo(MEUS_VIDEOS_CSV))


# Diagnostica um video especifico do meu canal, mostrando quais sinais chegaram ate a
# deteccao sem revelar chave de API nem dados pessoais de comentarios.
def diagnosticar_meu_video_interativo(video_id: str) -> None:
    if ler_chave_youtube() is None:
        print(
            "YOUTUBE_API_KEY nao definida no ambiente. "
            "Defina a variavel antes de diagnosticar um video (veja .env.example)."
        )
        return

    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    try:
        detalhe = coletar_detalhe_video(video_id)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    if detalhe is None:
        print(f"Video nao encontrado: {video_id}")
        return

    try:
        comentarios = coletar_textos_comentarios(
            video_id, 50, channel_id_dono=ler_id_canal_proprio()
        )
    except RuntimeError as erro:
        print(
            f"AVISO: video {video_id}: operacao comentarios falhou ({erro}). "
            "O diagnostico continuara sem comentarios completos."
        )
        comentarios = ComentariosColetados(incompleto=True)

    deteccao = detectar_jogo_em_conteudo(
        jogos,
        titulo=detalhe.titulo,
        descricao=detalhe.descricao,
        tags=detalhe.tags,
        comentarios=comentarios.textos,
        comentarios_analisados=comentarios.analisados,
    )

    print("=== Diagnostico do Meu Video ===")
    print(f"Video ID: {detalhe.video_id}")
    print(f"Titulo: {detalhe.titulo}")
    print(f"Descricao coletada: {'sim' if detalhe.descricao.strip() else 'nao'}")
    print(f"Trecho da descricao: {_trecho(detalhe.descricao)}")
    print(f"Tags coletadas: {len(detalhe.tags)}")
    if detalhe.tags:
        print(f"Tags: {', '.join(detalhe.tags)}")
    print(
        "Comentarios coletados: "
        f"{comentarios.comentarios_principais} principais, {comentarios.respostas} respostas"
    )
    print(f"Comentarios incompletos: {'sim' if comentarios.incompleto else 'nao'}")
    # Os dois sinais que a deteccao por comentario usa. Sem eles, um video sem jogo parece
    # sempre o mesmo caso; com eles da para ver se faltou o dono responder ou faltou alguem
    # perguntar. Contagens, nunca quem escreveu.
    print(
        "Comentarios do dono: "
        f"{sum(1 for c in comentarios.analisados if c.do_dono)} | "
        "em thread que pergunta o jogo: "
        f"{sum(1 for c in comentarios.analisados if c.responde_pergunta_de_jogo)}"
    )
    print(f"Jogo detectado: {deteccao.jogo_detectado or '(nenhum)'}")
    print(f"Fonte da deteccao: {deteccao.fonte}")
    print(f"Confianca: {deteccao.confianca}")
    print(f"Motivo da nao deteccao: {deteccao.motivo_nao_detectado or '(nao se aplica)'}")
    print(f"Nome extraido fora do seed: {'sim' if not deteccao.jogo_no_seed else 'nao'}")


# Encurta texto longo para diagnostico de terminal.
def _trecho(texto: str, limite: int = 180) -> str:
    texto = " ".join((texto or "").split())
    if not texto:
        return "(vazio)"
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "..."


# Cruza o ranking atual com os meus videos (data/meus_videos.csv) e mostra, por jogo,
# se a recomendacao funcionou comigo. Nao altera o ranking.
def comparar_recomendacoes_meu_canal_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    comparacoes = comparar_recomendacoes_com_meu_canal(ranking, meus_videos)
    imprimir_comparacao_meu_canal(comparacoes)


# Cruza o ranking atual com os meus videos e lista os jogos que ja funcionaram comigo e
# ainda tem janela aberta (candidatos a repeticao). Nao altera o ranking.
def jogos_para_repetir_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    imprimir_jogos_para_repetir(jogos_para_repetir(ranking, meus_videos))


# Cruza o ranking atual com os meus videos e lista os jogos de alta evidencia externa que
# mesmo assim renderam pouco comigo (prometiam mas falharam). Nao altera o ranking.
def jogos_que_nao_funcionaram_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    imprimir_jogos_que_nao_funcionaram(jogos_que_nao_funcionaram(ranking, meus_videos))


# Gera o relatorio de aprendizado do meu canal em Markdown, com timestamp no nome.
def relatorio_meu_canal_interativo() -> None:
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    caminho_relatorio = REPORTS_DIR / f"meu_canal_{data_hora}.md"
    gerar_relatorio_meu_canal_markdown(caminho_relatorio, meus_videos)
    print(f"Relatorio gerado em: {caminho_relatorio}")


# Valida a qualidade dos dados antes de confiar no ranking. So leitura, nao altera nada.
def validar_dados_interativo() -> None:
    videos = ler_videos_coletados(VIDEOS_CSV)
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    problemas = validar_dados(
        videos,
        jogos,
        canais,
        meus_videos,
        chave_configurada=ler_chave_youtube() is not None,
        canal_configurado=ler_id_canal_proprio() is not None,
        colunas_faltando_meus_videos=colunas_faltando(MEUS_VIDEOS_CSV),
    )
    imprimir_validacao(problemas)


# Mostra um health-check do sistema: configuracoes e quantidades de dados. So leitura.
# Usa o config centralizado (obter_*) e so reporta configurado/nao — nunca a chave real.
def status_sistema_interativo() -> None:
    status = coletar_status(
        chave_configurada=obter_youtube_api_key() is not None,
        canal_configurado=obter_meu_canal_youtube_id() is not None,
        caminho_videos=VIDEOS_CSV,
        caminho_meus_videos=MEUS_VIDEOS_CSV,
        caminho_jogos=DATA_DIR / "jogos_seed.csv",
        caminho_canais=DATA_DIR / "canais_referencia.csv",
        caminho_historico=HISTORICO_CSV,
        dir_relatorios=REPORTS_DIR,
    )
    imprimir_status(status)


# Executa o fluxo principal do dia a dia em um comando so, reusando os handlers existentes:
# coletar meu canal -> diagnostico -> ranking Top N -> oportunidades -> snapshot ->
# relatorios -> resumo. So a coleta toca a rede; o resto roda offline.
def rotina_diaria_interativo(
    limite: int,
    limite_comentarios: int,
    top: int | None = None,
    plataforma: str | None = None,
    desde: date | None = None,
    dry_run: bool = False,
) -> None:
    print("=== Rotina Diaria ===")
    if dry_run:
        print("(DRY-RUN: simulando, nada sera salvo)")
    print()

    resumo_coleta = _rotina_coletar_meu_canal(limite, limite_comentarios, dry_run)

    print()
    diagnosticar_dados_interativo()

    print()
    ranking = _carregar_ranking(plataforma, top, desde)
    imprimir_ranking(ranking)

    print()
    mostrar_oportunidades(plataforma, top, desde)

    print()
    if dry_run:
        print(f"DRY-RUN: salvaria um snapshot do ranking em {HISTORICO_CSV}.")
    else:
        salvar_snapshot_ranking_interativo(plataforma, top, desde)

    print()
    relatorios = _rotina_exportar_relatorios(plataforma, top, desde, dry_run)

    print()
    _imprimir_resumo_rotina(resumo_coleta, filtrar_oportunidades(ranking), relatorios)
    if dry_run:
        print()
        print("DRY-RUN: nada foi salvo (sem coleta, snapshot ou relatorios).")


# Passo de coleta da rotina: coleta e analisa o meu canal (reusa analisar_meu_canal). Pula
# de forma limpa, sem tocar a rede, se faltar chave ou canal. Com dry_run, so mostra o
# plano (sem API). Devolve o resumo ou None.
def _rotina_coletar_meu_canal(
    limite: int, limite_comentarios: int, dry_run: bool = False
) -> dict | None:
    if dry_run:
        _plano_coleta_meu_canal(limite, limite_comentarios)
        return None

    if ler_chave_youtube() is None or ler_id_canal_proprio() is None:
        print(
            "Coleta do canal pulada: YOUTUBE_API_KEY e/ou MEU_CANAL_YOUTUBE_ID nao "
            "configurados (rodando com os dados atuais)."
        )
        return None

    _migrar_meus_videos_se_preciso()
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    try:
        resumo = analisar_meu_canal(
            ler_id_canal_proprio(), jogos, MEUS_VIDEOS_CSV, limite, limite_comentarios
        )
    except RuntimeError as erro:
        print(f"Coleta do canal falhou: {erro} (rodando com os dados atuais).")
        return None

    print(
        f"Coleta do canal: {resumo['analisados']} analisados, "
        f"{resumo['jogos_detectados']} com jogo, {resumo['jogos_nao_detectados']} sem jogo."
    )
    return resumo


# Passo de relatorios da rotina: exporta ranking e calibracao em Markdown com timestamp.
# Devolve a lista de caminhos gerados. Com dry_run, so mostra o que seria gerado.
def _rotina_exportar_relatorios(
    plataforma: str | None, top: int | None, desde: date | None, dry_run: bool = False
) -> list[str]:
    if dry_run:
        print(f"DRY-RUN: geraria os relatorios de ranking e calibracao em {REPORTS_DIR}.")
        return []

    ranking = _carregar_ranking(plataforma, top, desde)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")

    caminho_ranking = REPORTS_DIR / f"ranking_{data_hora}.md"
    gerar_relatorio_markdown(caminho_ranking, ranking)
    caminho_calibracao = REPORTS_DIR / f"calibracao_ranking_{data_hora}.md"
    gerar_relatorio_calibracao_markdown(caminho_calibracao, ranking, meus_videos)

    relatorios = [str(caminho_ranking), str(caminho_calibracao)]
    for caminho in relatorios:
        print(f"Relatorio gerado: {caminho}")
    return relatorios


# Resumo final da rotina: numeros da coleta, relatorios e o topo das oportunidades.
def _imprimir_resumo_rotina(
    resumo_coleta: dict | None, oportunidades: list, relatorios: list[str]
) -> None:
    print("=== Resumo da Rotina ===")
    if resumo_coleta is None:
        print("Videos analisados: 0 (coleta pulada)")
        print("Jogos detectados: 0")
        print("Jogos nao detectados: 0")
    else:
        print(f"Videos analisados: {resumo_coleta['analisados']}")
        print(f"Jogos detectados: {resumo_coleta['jogos_detectados']}")
        print(f"Jogos nao detectados: {resumo_coleta['jogos_nao_detectados']}")
    print(f"Relatorios gerados: {len(relatorios)}")
    print(f"Top oportunidades: {len(oportunidades)}")
    for posicao, resultado in oportunidades[:5]:
        print(f"  #{posicao} {resultado.jogo.nome}")


# Gera o relatorio executivo do dia (ranking + meus videos + canais) em Markdown, com
# timestamp. Curto e voltado a decisao dos proximos jogos a testar.
def relatorio_diario_interativo(
    plataforma: str | None = None, top: int | None = None, desde: date | None = None
) -> None:
    ranking = _carregar_ranking(plataforma, top, desde)
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    caminho_relatorio = REPORTS_DIR / f"relatorio_diario_{data_hora}.md"
    gerar_relatorio_diario_markdown(caminho_relatorio, ranking, meus_videos, canais)
    print(f"Relatorio gerado em: {caminho_relatorio}")


# Gera o relatorio de calibracao (ranking atual x meus videos) em Markdown, com timestamp.
def relatorio_calibracao_interativo() -> None:
    ranking = _carregar_ranking()
    meus_videos = ler_meus_videos(MEUS_VIDEOS_CSV)
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    caminho_relatorio = REPORTS_DIR / f"calibracao_ranking_{data_hora}.md"
    gerar_relatorio_calibracao_markdown(caminho_relatorio, ranking, meus_videos)
    print(f"Relatorio gerado em: {caminho_relatorio}")


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


# Mostra os criadores/videos detectados para um jogo especifico, por viralidade.
# Com tipo (curto/longo/live/desconhecido) filtra apenas os videos daquele formato.
def evidencias_jogo_interativo(nome_jogo: str, tipo: str | None = None) -> None:
    ranking = _carregar_ranking()
    canais = ler_canais_referencia(DATA_DIR / "canais_referencia.csv")
    evidencias_por_jogo = gerar_evidencias(ranking, canais)

    alvo = nome_jogo.strip().casefold()
    encontrado = next(
        (nome for nome in evidencias_por_jogo if nome.casefold() == alvo), None
    )
    if encontrado is None or not evidencias_por_jogo[encontrado]:
        print(f"Nenhum video encontrado para o jogo: {nome_jogo}")
        return

    evidencias = evidencias_por_jogo[encontrado]
    if tipo:
        evidencias = [e for e in evidencias if e.tipo_video == tipo]
        if not evidencias:
            print(f"Nenhum video do tipo '{tipo}' encontrado para o jogo: {encontrado}")
            return

    print(f"Jogo: {encontrado}")
    print(f"Score de evidencia: {calcular_score_evidencia_criadores(evidencias):.1f}")
    print(f"Resumo: {resumir_evidencia_criadores(evidencias)}")
    print()
    print("Videos:")
    for posicao, evidencia in enumerate(evidencias, start=1):
        print(
            f"{posicao}. {evidencia.canal} | {evidencia.nicho} | "
            f"{evidencia.tipo_conteudo} | {evidencia.plataforma} | "
            f"{evidencia.tipo_video} | {evidencia.views} views | "
            f"{evidencia.taxa_engajamento:.1f}% engajamento | "
            f"similaridade {evidencia.peso_similaridade:.1f} | "
            f"score {evidencia.score_viralidade_video:.1f}"
        )
        print(f"   Titulo: {evidencia.titulo}")
        print(f"   Link: {evidencia.url}")
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
            tipo_video=_perguntar_tipo_video(),
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


# Pergunta o tipo do video; vazio assume "desconhecido".
def _perguntar_tipo_video() -> str:
    valor = input("tipo_video (curto/longo/live) [desconhecido]: ").strip()
    return valor or "desconhecido"


# Fabrica um validador de inteiro para o `type=` do argparse. Precisa ser uma fabrica
# porque o argparse so entrega o VALOR para a funcao de validacao — o nome da flag e o
# minimo ficam guardados no fechamento, para cada flag errar com a sua propria mensagem.
# minimo=1 e o caso comum (quantidade precisa ser positiva); minimo=0 e para as flags
# em que zero significa "desligado", como --comentarios-extra-sem-jogo.
# --fit e o palpite a priori de encaixe do jogo no canal, na escala 0-10 do jogos_seed.csv
# (o ranker multiplica por 10). Fora da faixa nao quebra nada — o ranker limita — mas vira
# um numero mentiroso no arquivo, entao e melhor recusar na entrada.
def _fit_valido(valor: str) -> float:
    try:
        numero = float(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"valor invalido para --fit: {valor}")
    if not 0.0 <= numero <= 10.0:
        raise argparse.ArgumentTypeError(f"--fit deve ficar entre 0 e 10: {valor}")
    return numero


def _inteiro(nome_flag: str, minimo: int = 1):
    def _validar(valor: str) -> int:
        try:
            numero = int(valor)
        except ValueError:
            raise argparse.ArgumentTypeError(f"valor invalido para {nome_flag}: {valor}")
        if numero < minimo:
            raise argparse.ArgumentTypeError(
                f"{nome_flag} deve ser um inteiro maior ou igual a {minimo}: {valor}"
            )
        return numero

    return _validar


# Validador do --top (inteiro positivo), mantido com nome proprio por ser o mais usado.
_top_valido = _inteiro("--top")


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
# Cheat-sheet por categoria + exemplos, mostrado no fim de `--help`. argparse nao agrupa
# subcomandos por categoria na lista automatica, entao a organizacao por tema vive aqui.
_EPILOGO_AJUDA = """\
Categorias de comandos:
  Ranking:        ranking, exportar_ranking, oportunidades
  Coleta:         adicionar_video, importar_videos, coletar_video_youtube,
                  coletar_videos_youtube, coletar_canal_youtube
  Meu canal:      listar_meus_videos_youtube, coletar_meu_canal, meus_videos_sem_jogo,
                  comparar_recomendacoes_meu_canal, jogos_para_repetir,
                  jogos_que_nao_funcionaram
  Evidencias:     evidencias_jogo, exportar_evidencias_jogos
  Relatorios:     relatorio_diario, relatorio_meu_canal, relatorio_calibracao
  Monitoramento:  salvar_snapshot_ranking, comparar_rankings, ranking_watchlist,
                  adicionar_watchlist, listar_watchlist, remover_watchlist
  Qualidade:      validar_dados, diagnosticar_dados, videos_sem_jogo, adicionar_jogo,
                  adicionar_alias, redetectar_meus_videos, status_sistema
  Rotina:         rotina_diaria (faz o fluxo do dia inteiro em um comando)

Exemplos:
  python src/main.py ranking --top 10
  python src/main.py rotina_diaria --limite 20 --comentarios 50 --top 10
  python src/main.py coletar_meu_canal --limite 10 --dry-run
  python src/main.py validar_dados
  python src/main.py evidencias_jogo "R.E.P.O." --tipo curto

Filtros comuns (ranking e relatorios): --plataforma NOME, --desde AAAA-MM-DD, --top N.
Detalhes de um comando: python src/main.py <comando> --help
"""


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recomenda games para Shorts, Reels e TikTok, calibrado pelos resultados reais "
            "do seu canal. Roda offline sobre CSVs locais; so a coleta do YouTube usa rede."
        ),
        epilog=_EPILOGO_AJUDA,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subcomandos = parser.add_subparsers(dest="comando", title="comandos", metavar="<comando>")

    ranking = subcomandos.add_parser(
        "ranking",
        help="Mostra o ranking de jogos recomendados no terminal (comando padrao).",
    )
    _adicionar_filtros(ranking)

    exportar = subcomandos.add_parser(
        "exportar_ranking",
        help="Exporta o ranking para um arquivo (Markdown ou CSV) datado em reports/.",
    )
    _adicionar_filtros(exportar)
    exportar.add_argument(
        "--formato",
        choices=["md", "csv"],
        default="md",
        help="Formato do arquivo exportado: md ou csv (padrao: md).",
    )

    subcomandos.add_parser(
        "adicionar_video",
        help="Cadastra um video de referencia manualmente (perguntas interativas).",
    )

    importar = subcomandos.add_parser(
        "importar_videos",
        help="Importa videos de referencia em lote de um CSV externo (valida e ignora duplicados).",
    )
    importar.add_argument("origem", help="Caminho do CSV externo a importar.")

    subcomandos.add_parser(
        "diagnosticar_dados",
        help="Resume a qualidade dos videos coletados (por plataforma, canal, origem).",
    )

    subcomandos.add_parser(
        "videos_sem_jogo",
        help="Lista videos de referencia sem jogo detectado, por views (ache aliases faltando).",
    )

    jogo_parser = subcomandos.add_parser(
        "adicionar_jogo",
        help="Cadastra um jogo novo no jogos_seed.csv (o detector so enxerga o que esta la).",
    )
    jogo_parser.add_argument("nome", help="Nome do jogo, como deve aparecer no ranking.")
    jogo_parser.add_argument(
        "--aliases",
        default="",
        help="Aliases separados por | (padrao: o proprio nome em minusculas).",
    )
    jogo_parser.add_argument(
        "--genero", default="", help="Genero do jogo (ex: horror coop)."
    )
    jogo_parser.add_argument(
        "--fit",
        type=_fit_valido,
        default=5.0,
        help="Fit inicial de 0 a 10: o palpite de encaixe no seu canal (padrao: 5).",
    )

    alias_parser = subcomandos.add_parser(
        "adicionar_alias",
        help="Adiciona um alias a um jogo do jogos_seed.csv (melhora a deteccao).",
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
        type=_inteiro("--limite"),
        default=5,
        help="Quantos videos recentes coletar (padrao: 5).",
    )

    meus_videos = subcomandos.add_parser(
        "listar_meus_videos_youtube",
        help="Lista os IDs e titulos dos seus videos recentes do YouTube (nao salva no CSV).",
    )
    meus_videos.add_argument(
        "--limite",
        type=_inteiro("--limite"),
        default=10,
        help="Quantos videos recentes listar (padrao: 10).",
    )

    meu_canal = subcomandos.add_parser(
        "coletar_meu_canal",
        help="Coleta e analisa seus videos recentes, detecta o jogo e salva em meus_videos.csv.",
    )
    meu_canal.add_argument(
        "--limite",
        type=_inteiro("--limite"),
        default=None,
        help="Sem --todos-videos: quantos recentes analisar (padrao: 5). Com --todos-videos: teto opcional.",
    )
    meu_canal.add_argument(
        "--todos-videos",
        action="store_true",
        help="Coleta TODOS os videos do canal (paginado, incremental e economico), nao so os recentes.",
    )
    meu_canal.add_argument(
        "--comentarios",
        type=_inteiro("--comentarios"),
        default=20,
        help="Comentarios por video, so onde o jogo nao foi detectado por titulo/descricao/tags (padrao: 20).",
    )
    meu_canal.add_argument(
        "--comentarios-extra-sem-jogo",
        type=_inteiro("--comentarios-extra-sem-jogo", minimo=0),
        default=0,
        help="Comentarios extra so nos videos que continuarem sem jogo (0 = desligado).",
    )
    meu_canal.add_argument(
        "--forcar",
        action="store_true",
        help="Com --todos-videos: reanalisa tambem os videos ja salvos (recoleta descricao, tags e metricas).",
    )
    meu_canal.add_argument(
        "--todos-comentarios",
        action="store_true",
        help="(Ainda nao recomendado) buscaria todos os comentarios; atualmente apenas avisa e e ignorado.",
    )
    meu_canal.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula: mostra o plano e o custo de quota, sem chamar a API nem salvar.",
    )

    redetectar = subcomandos.add_parser(
        "redetectar_meus_videos",
        help="Recalcula o jogo dos seus videos ja salvos, sem rede e sem gastar quota.",
    )
    redetectar.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula: mostra o que mudaria, sem escrever no meus_videos.csv.",
    )

    subcomandos.add_parser(
        "meus_videos_sem_jogo",
        help="Lista os seus videos coletados sem jogo detectado, com sugestao para corrigir.",
    )

    diagnosticar_meu_video = subcomandos.add_parser(
        "diagnosticar_meu_video",
        help="Mostra os sinais de deteccao de um video especifico do meu canal.",
    )
    diagnosticar_meu_video.add_argument("video_id", help="ID do video do YouTube.")

    comparar_meu_canal = subcomandos.add_parser(
        "comparar_recomendacoes_meu_canal",
        help="Cruza o ranking com os seus videos para ver se a recomendacao funcionou comigo.",
    )
    _adicionar_filtros(comparar_meu_canal)

    subcomandos.add_parser(
        "relatorio_meu_canal",
        help="Gera um relatorio Markdown do que funcionou no seu canal (jogos e formatos).",
    )

    subcomandos.add_parser(
        "relatorio_calibracao",
        help="Gera um relatorio Markdown de como os dados do seu canal influenciam o ranking.",
    )

    relatorio_diario = subcomandos.add_parser(
        "relatorio_diario",
        help="Gera um relatorio executivo curto do dia para decidir os proximos jogos.",
    )
    _adicionar_filtros(relatorio_diario)

    subcomandos.add_parser(
        "validar_dados",
        help="Checklist de qualidade dos dados antes de confiar no ranking (info/aviso/critico).",
    )

    subcomandos.add_parser(
        "status_sistema",
        help="Mostra um health-check: configuracoes e quantidades de dados (so leitura).",
    )

    rotina = subcomandos.add_parser(
        "rotina_diaria",
        help="Executa o fluxo diario completo: coleta, diagnostico, ranking, snapshot e relatorios.",
    )
    _adicionar_filtros(rotina)
    rotina.add_argument(
        "--limite",
        type=_inteiro("--limite"),
        default=5,
        help="Quantos videos do meu canal coletar (padrao: 5).",
    )
    rotina.add_argument(
        "--comentarios",
        type=_inteiro("--comentarios"),
        default=20,
        help="Quantos comentarios por video puxar na coleta (padrao: 20).",
    )
    rotina.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula o fluxo: nao coleta, nao salva snapshot e nao gera relatorios.",
    )

    repetir = subcomandos.add_parser(
        "jogos_para_repetir",
        help="Lista jogos que ja funcionaram comigo e ainda tem janela aberta (vale repetir).",
    )
    _adicionar_filtros(repetir)

    nao_funcionaram = subcomandos.add_parser(
        "jogos_que_nao_funcionaram",
        help="Lista jogos de alta evidencia externa que renderam pouco comigo (nao repetir cego).",
    )
    _adicionar_filtros(nao_funcionaram)

    snapshot = subcomandos.add_parser(
        "salvar_snapshot_ranking",
        help="Calcula o ranking e acrescenta um snapshot ao historico.",
    )
    _adicionar_filtros(snapshot)

    subcomandos.add_parser(
        "comparar_rankings",
        help="Compara as duas ultimas execucoes do historico (o que subiu, caiu, entrou, saiu).",
    )

    oportunidades = subcomandos.add_parser(
        "oportunidades",
        help="Atalho do ranking so com os jogos de janela aberta (alta oportunidade).",
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

    evidencias = subcomandos.add_parser(
        "evidencias_jogo",
        help="Lista os criadores/videos detectados para um jogo especifico.",
    )
    evidencias.add_argument("jogo", help="Nome do jogo (igual ao do jogos_seed.csv).")
    evidencias.add_argument(
        "--tipo",
        choices=["curto", "longo", "live", "desconhecido"],
        help="Mostra apenas os videos deste formato (curto, longo, live ou desconhecido).",
    )

    exportar_evidencias = subcomandos.add_parser(
        "exportar_evidencias_jogos",
        help="Exporta para Markdown os jogos e os videos/criadores que servem de evidencia.",
    )
    _adicionar_filtros(exportar_evidencias)

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
