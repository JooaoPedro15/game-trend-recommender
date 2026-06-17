# Jogos para repetir (Sprint 9.5): cruza o ranking atual com os meus videos para achar
# jogos que JA funcionaram comigo e cuja janela de mercado ainda esta aberta — candidatos
# a outro teste, com menos risco que um jogo novo. Funcao de cruzamento pura (ranking +
# meus_videos injetados). So aponta oportunidade e formato; nunca cria ideia de video.

from dataclasses import dataclass

from fit_canal import agrupar_meus_videos_por_jogo
from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo, ResultadoRecomendacao


# Limiares (heuristicas do MVP, calibrar depois): funcionou bem comigo, janela ainda
# relevante e mercado nao saturado demais (saturacao <= 40 e o veto de "evitar").
RESULTADO_BOM = 60.0
OPORTUNIDADE_RELEVANTE = 50.0
SATURACAO_MINIMA = 45.0


# Um jogo candidato a repeticao, com o porque numerico.
@dataclass
class CandidatoRepeticao:
    jogo: str
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    score_oportunidade: float
    tipo_video: str
    motivo: str


# Lista os jogos que valem outro teste: para cada jogo do ranking com historico no meu
# canal, pega o meu melhor video; mantem so os que funcionaram bem comigo E ainda tem
# janela aberta E nao estao saturados. Ordena pelo resultado real (depois pela oportunidade).
def jogos_para_repetir(
    ranking: list[ResultadoRecomendacao], meus_videos: list[MeuVideo]
) -> list[CandidatoRepeticao]:
    por_jogo = agrupar_meus_videos_por_jogo(meus_videos)

    candidatos = []
    for resultado in ranking:
        melhor = _melhor_video(por_jogo.get(resultado.jogo.nome.casefold(), []))
        if melhor is None:
            continue

        score_real = calcular_score_resultado_real(melhor)
        if not _merece_repeticao(score_real, resultado):
            continue

        candidatos.append(
            CandidatoRepeticao(
                jogo=resultado.jogo.nome,
                melhor_video_titulo=melhor.titulo,
                melhor_video_url=melhor.url,
                score_resultado_real=score_real,
                score_oportunidade=resultado.score_oportunidade,
                tipo_video=melhor.tipo_video,
                motivo=_motivo(score_real, melhor.tipo_video, resultado.score_oportunidade),
            )
        )

    candidatos.sort(
        key=lambda c: (c.score_resultado_real, c.score_oportunidade), reverse=True
    )
    return candidatos


# O meu video de melhor resultado real do grupo (None se vazio).
def _melhor_video(videos: list[MeuVideo]) -> MeuVideo | None:
    if not videos:
        return None
    return max(videos, key=calcular_score_resultado_real)


# Vale repetir quando funcionou bem comigo, a janela ainda e relevante e nao esta saturado.
def _merece_repeticao(score_real: float, resultado: ResultadoRecomendacao) -> bool:
    return (
        score_real >= RESULTADO_BOM
        and resultado.score_oportunidade >= OPORTUNIDADE_RELEVANTE
        and resultado.score_saturacao >= SATURACAO_MINIMA
    )


# Motivo operacional curto (sem roteiro/tom): o que funcionou e por que a janela vale.
def _motivo(score_real: float, tipo_video: str, score_oportunidade: float) -> str:
    return (
        f"Ja funcionou comigo em {tipo_video} (resultado {score_real:.0f}); "
        f"janela ainda aberta (oportunidade {score_oportunidade:.0f})."
    )


# Mostra os candidatos a repeticao no terminal, de forma simples e legivel.
def imprimir_jogos_para_repetir(candidatos: list[CandidatoRepeticao]) -> None:
    print("=== Jogos para Repetir ===")
    print()
    if not candidatos:
        print("Nenhum jogo que funcionou comigo tem janela aberta no momento.")
        print("Criterios: resultado real >= 60, oportunidade >= 50, saturacao >= 45.")
        return

    for candidato in candidatos:
        print(f"- {candidato.jogo}")
        print(
            f"  Resultado real: {candidato.score_resultado_real:.1f} | "
            f"Oportunidade: {candidato.score_oportunidade:.1f} | "
            f"Formato que funcionou: {candidato.tipo_video}"
        )
        print(f"  Melhor video meu: {candidato.melhor_video_titulo}")
        print(f"  Link: {candidato.melhor_video_url}")
        print(f"  Motivo: {candidato.motivo}")
        print()
