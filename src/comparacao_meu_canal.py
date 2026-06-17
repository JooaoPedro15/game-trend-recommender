# Feedback loop da Sprint 8: cruza as recomendacoes do sistema (ranking) com o
# resultado real dos meus videos (meus_videos.csv) para auditar se cada aposta
# funcionou comigo. Funcao de cruzamento pura (ranking + meus_videos injetados);
# o main.py le o ranking e o CSV e injeta aqui. Nao mexe no ranking.

from dataclasses import dataclass

from meus_videos import calcular_score_resultado_real
from modelos import MeuVideo, ResultadoRecomendacao


# Limiares simples (heuristicas do MVP, calibrar depois). score_final reusa o mesmo
# corte de "aposta alta" das oportunidades (>= 60); o resultado real usa duas faixas.
RECOMENDADO_ALTO = 60.0
RESULTADO_BOM = 60.0
RESULTADO_FRACO = 40.0


# Uma linha do confronto recomendacao x resultado real, para um jogo do ranking.
@dataclass
class ComparacaoJogo:
    jogo: str
    score_final: float
    score_oportunidade: float
    score_evidencia_nicho: float
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    conclusao: str


# Para cada jogo recomendado no ranking, acha o melhor video meu daquele jogo (se houver)
# e gera a conclusao do confronto. Funcao pura: nao le disco nem rede.
def comparar_recomendacoes_com_meu_canal(
    ranking: list[ResultadoRecomendacao], meus_videos: list[MeuVideo]
) -> list[ComparacaoJogo]:
    por_jogo = _agrupar_meus_videos_por_jogo(meus_videos)

    comparacoes = []
    for resultado in ranking:
        videos = por_jogo.get(resultado.jogo.nome.casefold(), [])
        melhor = _melhor_video(videos)
        score_real = calcular_score_resultado_real(melhor) if melhor is not None else 0.0
        comparacoes.append(
            ComparacaoJogo(
                jogo=resultado.jogo.nome,
                score_final=resultado.score_final,
                score_oportunidade=resultado.score_oportunidade,
                score_evidencia_nicho=resultado.score_evidencia_nicho,
                melhor_video_titulo=melhor.titulo if melhor is not None else "",
                melhor_video_url=melhor.url if melhor is not None else "",
                score_resultado_real=score_real,
                conclusao=_concluir(resultado, melhor, score_real),
            )
        )
    return comparacoes


# Agrupa os meus videos por jogo detectado (chave em casefold). Videos sem jogo ficam de fora.
def _agrupar_meus_videos_por_jogo(meus_videos: list[MeuVideo]) -> dict[str, list[MeuVideo]]:
    grupos: dict[str, list[MeuVideo]] = {}
    for video in meus_videos:
        chave = video.jogo_detectado.strip().casefold()
        if chave:
            grupos.setdefault(chave, []).append(video)
    return grupos


# O meu video de melhor resultado real do grupo (None se o grupo estiver vazio).
def _melhor_video(videos: list[MeuVideo]) -> MeuVideo | None:
    if not videos:
        return None
    return max(videos, key=calcular_score_resultado_real)


# Veredito por regras simples (sem IA), cruzando a aposta do sistema (score_final) com o
# resultado real do meu melhor video:
#   sem video do jogo            -> ainda_nao_testado
#   apostou alto e funcionou     -> recomendacao_confirmada
#   apostou alto e foi fraco     -> prometia_mas_nao_funcionou
#   nao apostou alto e funcionou -> funcionou_melhor_que_o_esperado
#   resto (zona cinzenta)        -> precisa_de_mais_testes
def _concluir(
    resultado: ResultadoRecomendacao, melhor: MeuVideo | None, score_real: float
) -> str:
    if melhor is None:
        return "ainda_nao_testado"

    apostou_alto = resultado.score_final >= RECOMENDADO_ALTO
    funcionou = score_real >= RESULTADO_BOM
    foi_fraco = score_real < RESULTADO_FRACO

    if apostou_alto and funcionou:
        return "recomendacao_confirmada"
    if apostou_alto and foi_fraco:
        return "prometia_mas_nao_funcionou"
    if not apostou_alto and funcionou:
        return "funcionou_melhor_que_o_esperado"
    return "precisa_de_mais_testes"


# Mostra o confronto no terminal, de forma simples e legivel.
def imprimir_comparacao_meu_canal(comparacoes: list[ComparacaoJogo]) -> None:
    print("=== Recomendacoes vs Resultado no Meu Canal ===")
    print()
    if not comparacoes:
        print("Ranking vazio: nenhum jogo para comparar.")
        return

    for comparacao in comparacoes:
        print(f"- {comparacao.jogo}  [{comparacao.conclusao}]")
        print(
            f"  Recomendado: final {comparacao.score_final:.1f} | "
            f"oportunidade {comparacao.score_oportunidade:.1f} | "
            f"evidencia nicho {comparacao.score_evidencia_nicho:.1f}"
        )
        if comparacao.melhor_video_titulo:
            print(
                f"  Melhor video meu: {comparacao.melhor_video_titulo} "
                f"(resultado real {comparacao.score_resultado_real:.1f})"
            )
            print(f"    {comparacao.melhor_video_url}")
        else:
            print("  Melhor video meu: (nenhum vinha desse jogo)")
        print()
