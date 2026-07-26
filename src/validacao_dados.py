# Checklist de qualidade dos dados (Sprint 10.5): antes de confiar no ranking, aponta
# problemas que deixariam a recomendacao ruim. So leitura e analise — nao altera nenhum
# dado, nao toca a API. Recebe os dados ja carregados e os booleanos de config injetados.
# Cada problema tem severidade (info/aviso/critico) e uma sugestao operacional simples.

from dataclasses import dataclass
from datetime import date

from diagnostico_dados import encontrar_videos_sem_jogo
from meus_videos import calcular_score_resultado_real
from modelos import CanalReferencia, JogoSeed, MeuVideo, VideoColetado


# A partir de qual proporcao de tipo_video "desconhecido" o problema vira aviso (heuristica).
LIMIAR_TIPO_DESCONHECIDO = 0.5


# Um problema encontrado na validacao. severidade: info | aviso | critico.
@dataclass
class Problema:
    severidade: str
    mensagem: str
    sugestao: str


# Valida a qualidade dos dados e devolve a lista de problemas (vazia = tudo ok). Funcao
# pura: nao le disco nem a API, nao altera nada.
def validar_dados(
    videos: list[VideoColetado],
    jogos: list[JogoSeed],
    canais: list[CanalReferencia],
    meus_videos: list[MeuVideo],
    chave_configurada: bool,
    canal_configurado: bool,
    colunas_faltando_meus_videos: list[str] | None = None,
) -> list[Problema]:
    problemas: list[Problema] = []
    _validar_jogos(problemas, jogos)
    _validar_videos(problemas, videos, jogos)
    _validar_canais(problemas, canais)
    _validar_meus_videos(problemas, meus_videos, colunas_faltando_meus_videos or [])
    _validar_config(problemas, chave_configurada, canal_configurado)
    return problemas


def _validar_jogos(problemas: list[Problema], jogos: list[JogoSeed]) -> None:
    if not jogos:
        problemas.append(
            Problema(
                "critico",
                "Nenhum jogo no jogos_seed.csv.",
                "Cadastre jogos em data/jogos_seed.csv; sem jogos nada e detectado.",
            )
        )
        return

    sem_alias = [jogo for jogo in jogos if not jogo.aliases]
    if sem_alias:
        problemas.append(
            Problema(
                "info",
                f"{len(sem_alias)} de {len(jogos)} jogo(s) sem aliases.",
                "Adicione aliases (adicionar_alias) para detectar variacoes do nome.",
            )
        )


def _validar_videos(
    problemas: list[Problema], videos: list[VideoColetado], jogos: list[JogoSeed]
) -> None:
    if not videos:
        problemas.append(
            Problema(
                "critico",
                "Nenhum video em videos_coletados.csv.",
                "Colete videos (importar_videos / coletar_*_youtube) antes de confiar no ranking.",
            )
        )
        return

    sem_jogo = encontrar_videos_sem_jogo(videos, jogos)
    if len(sem_jogo) == len(videos):
        problemas.append(
            Problema(
                "critico",
                "Nenhum video coletado teve jogo detectado (o ranking ficaria vazio).",
                "Rode videos_sem_jogo e adicione aliases ou marque o jogo.",
            )
        )
    elif sem_jogo:
        problemas.append(
            Problema(
                "aviso",
                f"{len(sem_jogo)} de {len(videos)} video(s) sem jogo detectado.",
                "Rode videos_sem_jogo e adicione aliases para nao perder esse sinal.",
            )
        )

    zeradas = [video for video in videos if video.views <= 0]
    if zeradas:
        problemas.append(
            Problema(
                "aviso",
                f"{len(zeradas)} video(s) com views zeradas.",
                "Revise os dados; views=0 zera o peso do video na tendencia.",
            )
        )

    sem_data = [video for video in videos if not _data_valida(video.data_publicacao)]
    if sem_data:
        problemas.append(
            Problema(
                "aviso",
                f"{len(sem_data)} video(s) sem data valida.",
                "Preencha data_publicacao (YYYY-MM-DD); sem data, recencia e velocidade ficam neutras.",
            )
        )

    desconhecidos = [
        video for video in videos if (video.tipo_video or "desconhecido") == "desconhecido"
    ]
    if desconhecidos and len(desconhecidos) / len(videos) >= LIMIAR_TIPO_DESCONHECIDO:
        problemas.append(
            Problema(
                "aviso",
                f"{len(desconhecidos)} de {len(videos)} video(s) com tipo_video desconhecido.",
                "Preencha tipo_video (curto/longo/live) para a evidencia e o filtro por formato.",
            )
        )
    elif desconhecidos:
        problemas.append(
            Problema(
                "info",
                f"{len(desconhecidos)} video(s) com tipo_video desconhecido.",
                "Preencha tipo_video quando possivel.",
            )
        )


def _validar_canais(problemas: list[Problema], canais: list[CanalReferencia]) -> None:
    if not canais:
        problemas.append(
            Problema(
                "aviso",
                "Nenhum canal de referencia.",
                "Cadastre canais em data/canais_referencia.csv para ponderar a tendencia.",
            )
        )
        return

    sem_nicho = [canal for canal in canais if canal.nicho == "desconhecido"]
    if sem_nicho:
        problemas.append(
            Problema(
                "info",
                f"{len(sem_nicho)} de {len(canais)} canal(is) sem nicho definido.",
                "Defina nicho no canais_referencia.csv para enriquecer a evidencia.",
            )
        )

    neutros = [canal for canal in canais if canal.peso_similaridade <= 1.0]
    if len(neutros) == len(canais):
        problemas.append(
            Problema(
                "aviso",
                "Nenhum canal com peso_similaridade > 1.0; a evidencia de nicho fica desligada.",
                "Ajuste peso_similaridade dos canais parecidos com o seu nicho.",
            )
        )


def _validar_meus_videos(
    problemas: list[Problema],
    meus_videos: list[MeuVideo],
    colunas_faltando: list[str],
) -> None:
    if colunas_faltando:
        problemas.append(
            Problema(
                "aviso",
                f"meus_videos.csv esta sem {len(colunas_faltando)} coluna(s) do formato "
                f"atual: {', '.join(colunas_faltando)}.",
                "Rode coletar_meu_canal para atualizar o arquivo; sem descricao e tags a "
                "deteccao so enxerga o titulo.",
            )
        )

    if not meus_videos:
        return

    # Sem jogo detectado, o video existe mas nao ensina nada: fit real, jogos_para_repetir,
    # jogos_que_nao_funcionaram e o ajuste do ranking dependem todos do jogo_detectado.
    # Por isso 100% sem deteccao e critico, nao aviso — a calibracao inteira fica desligada
    # e, sem esta checagem, o comando terminava dizendo "nenhum problema encontrado".
    sem_jogo = [video for video in meus_videos if not video.jogo_detectado.strip()]
    if len(sem_jogo) == len(meus_videos):
        problemas.append(
            Problema(
                "critico",
                f"Nenhum dos {len(meus_videos)} video(s) do meu canal tem jogo detectado "
                "(fit real e toda a calibracao pelo canal ficam desligados).",
                "Rode meus_videos_sem_jogo e diagnosticar_meu_video <id> para ver o que "
                'falta; marque "Jogo: Nome" na descricao ou cadastre aliases.',
            )
        )
    elif sem_jogo:
        problemas.append(
            Problema(
                "aviso",
                f"{len(sem_jogo)} de {len(meus_videos)} video(s) do meu canal sem jogo "
                "detectado.",
                "Rode meus_videos_sem_jogo; cada video sem jogo e um resultado real perdido.",
            )
        )

    fora_do_seed = [
        video
        for video in meus_videos
        if video.jogo_detectado.strip() and not video.jogo_no_seed
    ]
    if fora_do_seed:
        problemas.append(
            Problema(
                "aviso",
                f"{len(fora_do_seed)} video(s) com jogo detectado que nao esta no "
                "jogos_seed.csv.",
                "Cadastre esses jogos em data/jogos_seed.csv para eles entrarem no ranking.",
            )
        )

    sem_resultado = [video for video in meus_videos if calcular_score_resultado_real(video) <= 0]
    if sem_resultado:
        problemas.append(
            Problema(
                "info",
                f"{len(sem_resultado)} dos meus videos sem resultado real mensuravel (views zeradas).",
                "Recolha com coletar_meu_canal; sem metricas nao da para medir o que funcionou.",
            )
        )


def _validar_config(
    problemas: list[Problema], chave_configurada: bool, canal_configurado: bool
) -> None:
    if not chave_configurada:
        problemas.append(
            Problema(
                "info",
                "YOUTUBE_API_KEY nao configurada (coleta indisponivel).",
                "Defina YOUTUBE_API_KEY para coletar; o ranking offline funciona sem ela.",
            )
        )
    if not canal_configurado:
        problemas.append(
            Problema(
                "info",
                "MEU_CANAL_YOUTUBE_ID nao configurado (calibracao pelo meu canal indisponivel).",
                "Defina MEU_CANAL_YOUTUBE_ID para coletar e calibrar pelo seu canal.",
            )
        )


# True se a data esta no formato ISO valido (YYYY-MM-DD).
def _data_valida(data_publicacao: str) -> bool:
    try:
        date.fromisoformat(data_publicacao)
        return True
    except ValueError:
        return False


# Mostra a validacao no terminal, do mais grave para o menos grave, com um resumo no fim.
def imprimir_validacao(problemas: list[Problema]) -> None:
    print("=== Validacao dos Dados ===")
    print()
    if not problemas:
        print("Nenhum problema encontrado. Dados prontos para o ranking.")
        return

    ordem = {"critico": 0, "aviso": 1, "info": 2}
    for problema in sorted(problemas, key=lambda p: ordem.get(p.severidade, 3)):
        print(f"[{problema.severidade.upper()}] {problema.mensagem}")
        print(f"  -> {problema.sugestao}")
    print()

    criticos = sum(1 for p in problemas if p.severidade == "critico")
    avisos = sum(1 for p in problemas if p.severidade == "aviso")
    infos = sum(1 for p in problemas if p.severidade == "info")
    print(f"Resumo: {criticos} critico(s), {avisos} aviso(s), {infos} info.")
