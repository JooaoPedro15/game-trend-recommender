import csv
from datetime import datetime
from pathlib import Path


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
