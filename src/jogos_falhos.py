# Jogos que prometiam mas nao funcionaram comigo (Sprint 9.6): o espelho de
# repetir_jogos. Cruza o ranking atual com os meus videos para achar jogos com alta
# evidencia externa (nicho + oportunidade) mas resultado baixo no meu canal — a armadilha
# de repetir um jogo so porque viralizou fora. Funcao de cruzamento pura (ranking +
# meus_videos injetados). So aponta o risco; nunca cria ideia de video.

from dataclasses import dataclass

from fit_canal import agrupar_meus_videos_por_jogo
from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo, ResultadoRecomendacao


# Limiares (heuristicas do MVP, calibrar depois): evidencia externa alta no meu nicho E
# janela de mercado alta, mas resultado real fraco comigo (mesmo corte do "falhou" da 8.9).
EVIDENCIA_NICHO_ALTA = 60.0
OPORTUNIDADE_ALTA = 60.0
RESULTADO_FRACO = 40.0


# Um jogo que prometia (evidencia externa alta) mas falhou comigo (resultado baixo).
@dataclass
class JogoQueFalhou:
    jogo: str
    score_evidencia_nicho: float
    score_oportunidade: float
    score_resultado_real: float
    tipo_video: str
    melhor_video_url: str
    conclusao: str


# Lista os jogos que prometiam mas nao funcionaram comigo: para cada jogo do ranking com
# historico no meu canal, pega o meu melhor video; mantem so os de evidencia externa alta
# (nicho E oportunidade) cujo melhor resultado ainda assim foi fraco. Ordena pela maior
# promessa externa primeiro (oportunidade desc), depois pelo pior resultado.
def jogos_que_nao_funcionaram(
    ranking: list[ResultadoRecomendacao], meus_videos: list[MeuVideo]
) -> list[JogoQueFalhou]:
    por_jogo = agrupar_meus_videos_por_jogo(meus_videos)

    falhos = []
    for resultado in ranking:
        melhor = _melhor_video(por_jogo.get(resultado.jogo.nome.casefold(), []))
        if melhor is None:
            continue

        score_real = calcular_score_resultado_real(melhor)
        if not _prometia_mas_falhou(score_real, resultado):
            continue

        falhos.append(
            JogoQueFalhou(
                jogo=resultado.jogo.nome,
                score_evidencia_nicho=resultado.score_evidencia_nicho,
                score_oportunidade=resultado.score_oportunidade,
                score_resultado_real=score_real,
                tipo_video=melhor.tipo_video,
                melhor_video_url=melhor.url,
                conclusao=_conclusao(melhor.tipo_video),
            )
        )

    falhos.sort(key=lambda j: (-j.score_oportunidade, j.score_resultado_real))
    return falhos


# O meu video de melhor resultado real do grupo (None se vazio). Mesmo no caso "falhou",
# olhamos o melhor video: se ate o melhor ficou fraco, a falha comigo e clara.
def _melhor_video(videos: list[MeuVideo]) -> MeuVideo | None:
    if not videos:
        return None
    return max(videos, key=calcular_score_resultado_real)


# Prometia (evidencia externa alta no nicho E oportunidade alta) mas o meu melhor resultado
# ficou abaixo do corte de "fraco".
def _prometia_mas_falhou(score_real: float, resultado: ResultadoRecomendacao) -> bool:
    return (
        resultado.score_evidencia_nicho >= EVIDENCIA_NICHO_ALTA
        and resultado.score_oportunidade >= OPORTUNIDADE_ALTA
        and score_real < RESULTADO_FRACO
    )


# Conclusao operacional curta (sem roteiro/tom): o alerta de nao repetir cegamente.
def _conclusao(tipo_video: str) -> str:
    return (
        f"Evidencia externa alta, mas falhou comigo em {tipo_video}; "
        "nao repetir so porque viralizou fora."
    )


# Mostra os jogos que prometiam mas falharam no terminal, de forma simples e legivel.
def imprimir_jogos_que_nao_funcionaram(falhos: list[JogoQueFalhou]) -> None:
    print("=== Jogos que Prometiam mas Nao Funcionaram Comigo ===")
    print()
    if not falhos:
        print("Nenhum jogo de alta evidencia externa teve resultado fraco no meu canal.")
        print("Criterios: evidencia nicho >= 60, oportunidade >= 60, resultado real < 40.")
        return

    for falho in falhos:
        print(f"- {falho.jogo}")
        print(
            f"  Evidencia externa: nicho {falho.score_evidencia_nicho:.1f} | "
            f"oportunidade {falho.score_oportunidade:.1f}"
        )
        print(
            f"  Resultado real: {falho.score_resultado_real:.1f} | "
            f"Formato testado: {falho.tipo_video}"
        )
        print(f"  Link: {falho.melhor_video_url}")
        print(f"  Conclusao: {falho.conclusao}")
        print()
