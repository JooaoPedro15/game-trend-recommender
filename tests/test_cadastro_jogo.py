import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cadastro_jogo import (
    JogoDuplicadoError,
    JogoNaoEncontradoError,
    adicionar_alias_jogo,
    adicionar_jogo_seed,
)
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


# --- Cadastro de jogo novo no seed: o detector so procura o que esta no seed ---
#
# Jogo detectado pela descricao ("Jogo: X") mas ausente do jogos_seed.csv fica num limbo:
# aparece no meus_videos.csv com jogo_no_seed=nao e nunca pode ser encontrado em nenhum
# outro video, porque a deteccao por alias so percorre o seed. So havia adicionar_alias,
# que exige o jogo ja existir — nao havia como criar o primeiro registro.

def _nomes(caminho):
    return [jogo.nome for jogo in ler_jogos_seed(caminho)]


def test_cadastra_jogo_novo_preservando_os_existentes(tmp_path):
    caminho = _criar_csv(tmp_path)

    adicionar_jogo_seed(caminho, "Lava and Aqua", ["lava e aqua"], "puzzle coop", 6.0)

    assert _nomes(caminho) == ["R.E.P.O.", "Minecraft", "Lava and Aqua"]
    novo = [j for j in ler_jogos_seed(caminho) if j.nome == "Lava and Aqua"][0]
    assert novo.aliases == ["lava e aqua"]
    assert novo.genero == "puzzle coop"
    assert novo.fit_inicial == 6.0
    assert _aliases(caminho, "R.E.P.O.") == ["repo", "r.e.p.o"]


def test_cadastra_jogo_com_valores_padrao(tmp_path):
    caminho = _criar_csv(tmp_path)

    adicionar_jogo_seed(caminho, "Apple Worm")

    novo = [j for j in ler_jogos_seed(caminho) if j.nome == "Apple Worm"][0]
    assert novo.aliases == ["apple worm"]  # o proprio nome vira alias
    assert novo.fit_inicial == 5.0


def test_cria_o_arquivo_quando_o_seed_nao_existe(tmp_path):
    caminho = tmp_path / "jogos_seed.csv"

    adicionar_jogo_seed(caminho, "Motion Soccer")

    assert _nomes(caminho) == ["Motion Soccer"]


def test_nome_duplicado_levanta_erro_e_nao_altera_csv(tmp_path):
    caminho = _criar_csv(tmp_path)
    antes = caminho.read_text(encoding="utf-8")

    with pytest.raises(JogoDuplicadoError):
        adicionar_jogo_seed(caminho, "minecraft")

    assert caminho.read_text(encoding="utf-8") == antes


def test_nome_que_colide_com_alias_existente_levanta_erro(tmp_path):
    caminho = _criar_csv(tmp_path)

    # "repo" ja e alias de R.E.P.O.; cadastrar um jogo com esse nome tornaria a
    # deteccao ambigua (o mesmo termo apontaria para dois jogos).
    with pytest.raises(JogoDuplicadoError):
        adicionar_jogo_seed(caminho, "Repo")


def test_alias_que_colide_com_termo_existente_levanta_erro(tmp_path):
    caminho = _criar_csv(tmp_path)
    antes = caminho.read_text(encoding="utf-8")

    with pytest.raises(JogoDuplicadoError):
        adicionar_jogo_seed(caminho, "Jogo Novo", ["MINE"])

    assert caminho.read_text(encoding="utf-8") == antes


def test_nome_vazio_levanta_erro(tmp_path):
    caminho = _criar_csv(tmp_path)

    with pytest.raises(ValueError):
        adicionar_jogo_seed(caminho, "   ")


def test_comando_adicionar_jogo_grava_no_seed(tmp_path, monkeypatch, capsys):
    import main

    caminho = _criar_csv(tmp_path)
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)

    assert main.main(["adicionar_jogo", "Lava and Aqua", "--genero", "puzzle"]) == 0

    assert "Lava and Aqua" in _nomes(caminho)
    assert "cadastrado" in capsys.readouterr().out.lower()


def test_comando_adicionar_jogo_duplicado_avisa_sem_quebrar(tmp_path, monkeypatch, capsys):
    import main

    caminho = _criar_csv(tmp_path)
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    antes = caminho.read_text(encoding="utf-8")

    assert main.main(["adicionar_jogo", "Minecraft"]) == 0

    assert caminho.read_text(encoding="utf-8") == antes
    assert "erro" in capsys.readouterr().out.lower()
