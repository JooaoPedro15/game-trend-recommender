import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from historico_ranking import CAMPOS_HISTORICO, salvar_snapshot
from modelos import JogoSeed, ResultadoRecomendacao


# Cria um resultado de ranking fake com valores padrao sobrescreviveis.
def _resultado(nome="R.E.P.O.", score_final=82.0):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=9.0),
        score_final=score_final,
        score_tendencia=70.0,
        score_fit_canal=90.0,
        score_descoberta=50.0,
        score_saturacao=90.0,
        videos_encontrados=2,
        canais_diferentes=1,
        motivo="Motivo de teste.",
        videos=[],
        score_oportunidade=76.0,
        acao_recomendada="Testar em Short",
    )


# Le as linhas de dados do CSV como dicionarios.
def _linhas(caminho):
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def test_salva_snapshot_com_cabecalho_e_dados(tmp_path):
    caminho = tmp_path / "historico.csv"
    ranking = [_resultado("R.E.P.O.", 82.0), _resultado("Minecraft", 60.0)]

    salvos = salvar_snapshot(caminho, ranking, data_execucao="2026-06-12 10:00:00")

    assert salvos == 2
    assert caminho.exists()

    primeira_linha = caminho.read_text(encoding="utf-8").splitlines()[0]
    assert primeira_linha == ",".join(CAMPOS_HISTORICO)

    linhas = _linhas(caminho)
    assert len(linhas) == 2
    assert linhas[0]["data_execucao"] == "2026-06-12 10:00:00"
    assert linhas[0]["posicao"] == "1"
    assert linhas[0]["nome_jogo"] == "R.E.P.O."
    assert linhas[0]["score_final"] == "82.0"
    assert linhas[0]["score_oportunidade"] == "76.0"
    assert linhas[0]["acao_recomendada"] == "Testar em Short"
    assert linhas[0]["motivo"] == "Motivo de teste."
    assert linhas[1]["posicao"] == "2"
    assert linhas[1]["nome_jogo"] == "Minecraft"


def test_segunda_chamada_acrescenta_sem_apagar(tmp_path):
    caminho = tmp_path / "historico.csv"

    salvar_snapshot(caminho, [_resultado("R.E.P.O.")], data_execucao="2026-06-12 10:00:00")
    salvar_snapshot(caminho, [_resultado("Minecraft")], data_execucao="2026-06-13 10:00:00")

    linhas = _linhas(caminho)
    assert len(linhas) == 2
    # o snapshot antigo continua intacto
    assert linhas[0]["nome_jogo"] == "R.E.P.O."
    assert linhas[0]["data_execucao"] == "2026-06-12 10:00:00"
    # e o novo foi acrescentado depois
    assert linhas[1]["nome_jogo"] == "Minecraft"
    assert linhas[1]["data_execucao"] == "2026-06-13 10:00:00"

    # o cabecalho nao foi duplicado na segunda escrita
    conteudo = caminho.read_text(encoding="utf-8")
    assert conteudo.count("data_execucao") == 1
