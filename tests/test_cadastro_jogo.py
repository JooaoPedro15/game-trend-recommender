import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cadastro_jogo import JogoNaoEncontradoError, adicionar_alias_jogo
from leitor_csv import ler_jogos_seed


# Cria um jogos_seed.csv temporario e devolve o caminho.
def _criar_csv(tmp_path):
    caminho = tmp_path / "jogos_seed.csv"
    caminho.write_text(
        "nome,aliases,genero,fit_inicial\n"
        "R.E.P.O.,repo|r.e.p.o,horror,9\n"
        "Minecraft,mine,sandbox,7\n",
        encoding="utf-8",
    )
    return caminho


# Le o CSV e retorna os aliases de um jogo pelo nome.
def _aliases(caminho, nome):
    for jogo in ler_jogos_seed(caminho):
        if jogo.nome == nome:
            return jogo.aliases
    return None


def test_adiciona_novo_alias_a_jogo_existente(tmp_path):
    caminho = _criar_csv(tmp_path)

    adicionado = adicionar_alias_jogo(caminho, "Minecraft", "minecraft 2")

    assert adicionado is True
    assert _aliases(caminho, "Minecraft") == ["mine", "minecraft 2"]
    # outros jogos preservados
    assert _aliases(caminho, "R.E.P.O.") == ["repo", "r.e.p.o"]


def test_nao_duplica_alias_existente(tmp_path):
    caminho = _criar_csv(tmp_path)

    adicionado = adicionar_alias_jogo(caminho, "Minecraft", "MINE")

    assert adicionado is False
    assert _aliases(caminho, "Minecraft") == ["mine"]


def test_busca_jogo_ignorando_maiusculas(tmp_path):
    caminho = _criar_csv(tmp_path)

    adicionado = adicionar_alias_jogo(caminho, "minecraft", "mc")

    assert adicionado is True
    assert "mc" in _aliases(caminho, "Minecraft")


def test_jogo_inexistente_levanta_erro_e_nao_altera_csv(tmp_path):
    caminho = _criar_csv(tmp_path)
    antes = caminho.read_text(encoding="utf-8")

    with pytest.raises(JogoNaoEncontradoError):
        adicionar_alias_jogo(caminho, "Schedule I", "schedule 1")

    assert caminho.read_text(encoding="utf-8") == antes
