import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from leitor_csv import _ler_linhas


CAMPOS_HISTORICO = [
    "data_execucao",
    "posicao",
    "nome_jogo",
    "score_final",
    "score_tendencia",
    "score_fit_canal",
    "score_descoberta",
    "score_saturacao",
    "score_oportunidade",
    "videos_encontrados",
    "canais_diferentes",
    "acao_recomendada",
    "motivo",
]


# Acrescenta um snapshot do ranking ao CSV historico (uma linha por jogo, com a
# data/hora da execucao). Nunca sobrescreve snapshots antigos: o arquivo e
# append-only, e o cabecalho e criado na primeira execucao.
def salvar_snapshot(
    caminho: str | Path, ranking, data_execucao: str | None = None
) -> int:
    caminho = Path(caminho)
    if data_execucao is None:
        data_execucao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _garantir_cabecalho(caminho)

    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_HISTORICO)
        for posicao, resultado in enumerate(ranking, start=1):
            escritor.writerow(
                {
                    "data_execucao": data_execucao,
                    "posicao": posicao,
                    "nome_jogo": resultado.jogo.nome,
                    "score_final": resultado.score_final,
                    "score_tendencia": resultado.score_tendencia,
                    "score_fit_canal": resultado.score_fit_canal,
                    "score_descoberta": resultado.score_descoberta,
                    "score_saturacao": resultado.score_saturacao,
                    "score_oportunidade": resultado.score_oportunidade,
                    "videos_encontrados": resultado.videos_encontrados,
                    "canais_diferentes": resultado.canais_diferentes,
                    "acao_recomendada": resultado.acao_recomendada,
                    "motivo": resultado.motivo,
                }
            )

    return len(ranking)


# Cria o arquivo com o cabecalho se ele ainda nao existir (ou estiver vazio).
def _garantir_cabecalho(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.stat().st_size > 0:
        return

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_HISTORICO)
        escritor.writeheader()


@dataclass
class VariacaoJogo:
    nome: str
    posicao_anterior: int
    posicao_atual: int
    variacao_score_final: float
    variacao_oportunidade: float


@dataclass
class ComparacaoRankings:
    data_anterior: str
    data_atual: str
    subiram: list[VariacaoJogo] = field(default_factory=list)
    cairam: list[VariacaoJogo] = field(default_factory=list)
    estaveis: list[VariacaoJogo] = field(default_factory=list)
    novos: list[str] = field(default_factory=list)
    sumiram: list[str] = field(default_factory=list)


# Compara as duas execucoes mais recentes do historico, alinhando os jogos por nome.
# Retorna None se o historico tiver menos de duas execucoes.
def comparar_ultimas_execucoes(caminho: str | Path) -> ComparacaoRankings | None:
    linhas = _ler_linhas(caminho)
    datas = sorted({linha["data_execucao"] for linha in linhas if linha.get("data_execucao")})
    if len(datas) < 2:
        return None

    data_anterior, data_atual = datas[-2], datas[-1]
    anterior = _jogos_da_execucao(linhas, data_anterior)
    atual = _jogos_da_execucao(linhas, data_atual)

    comparacao = ComparacaoRankings(data_anterior=data_anterior, data_atual=data_atual)
    comparacao.novos = sorted(set(atual) - set(anterior))
    comparacao.sumiram = sorted(set(anterior) - set(atual))

    for nome in atual:
        if nome not in anterior:
            continue
        variacao = VariacaoJogo(
            nome=nome,
            posicao_anterior=int(anterior[nome]["posicao"]),
            posicao_atual=int(atual[nome]["posicao"]),
            variacao_score_final=_delta(anterior[nome], atual[nome], "score_final"),
            variacao_oportunidade=_delta(anterior[nome], atual[nome], "score_oportunidade"),
        )
        if variacao.posicao_atual < variacao.posicao_anterior:
            comparacao.subiram.append(variacao)
        elif variacao.posicao_atual > variacao.posicao_anterior:
            comparacao.cairam.append(variacao)
        else:
            comparacao.estaveis.append(variacao)

    comparacao.subiram.sort(key=lambda v: v.posicao_anterior - v.posicao_atual, reverse=True)
    comparacao.cairam.sort(key=lambda v: v.posicao_atual - v.posicao_anterior, reverse=True)
    return comparacao


# Indexa por nome os jogos de uma execucao especifica.
def _jogos_da_execucao(linhas: list[dict], data_execucao: str) -> dict[str, dict]:
    return {
        linha["nome_jogo"]: linha
        for linha in linhas
        if linha.get("data_execucao") == data_execucao
    }


# Diferenca de um score entre duas linhas (0.0 quando o campo nao existe no historico antigo).
def _delta(linha_anterior: dict, linha_atual: dict, campo: str) -> float:
    return round(_float(linha_atual.get(campo)) - _float(linha_anterior.get(campo)), 1)


def _float(valor) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


# Formata uma variacao com sinal explicito (ex: +3.5 / -2.0).
def _com_sinal(valor: float) -> str:
    return f"{valor:+.1f}"


# Mostra a comparacao entre as duas ultimas execucoes no terminal.
def imprimir_comparacao(comparacao: ComparacaoRankings) -> None:
    print("=== Comparacao de Rankings ===")
    print(f"De {comparacao.data_anterior} para {comparacao.data_atual}")

    print()
    print("Subiram:")
    if not comparacao.subiram:
        print("  (nenhum)")
    for v in comparacao.subiram:
        print(
            f"  {v.nome}: {v.posicao_anterior} -> {v.posicao_atual} | "
            f"score {_com_sinal(v.variacao_score_final)} | "
            f"oportunidade {_com_sinal(v.variacao_oportunidade)}"
        )

    print()
    print("Cairam:")
    if not comparacao.cairam:
        print("  (nenhum)")
    for v in comparacao.cairam:
        print(
            f"  {v.nome}: {v.posicao_anterior} -> {v.posicao_atual} | "
            f"score {_com_sinal(v.variacao_score_final)} | "
            f"oportunidade {_com_sinal(v.variacao_oportunidade)}"
        )

    print()
    print("Novos no ranking:")
    if not comparacao.novos:
        print("  (nenhum)")
    for nome in comparacao.novos:
        print(f"  {nome}")

    print()
    print("Sumiram do ranking:")
    if not comparacao.sumiram:
        print("  (nenhum)")
    for nome in comparacao.sumiram:
        print(f"  {nome}")

    if comparacao.estaveis:
        print()
        print(f"Sem mudanca de posicao: {len(comparacao.estaveis)} jogo(s)")
