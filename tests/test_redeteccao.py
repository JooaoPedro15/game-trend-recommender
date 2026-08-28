import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leitor_csv import _ler_linhas
from meus_videos import salvar_meu_video
from modelos import JogoSeed, MeuVideo
from redeteccao import aplicar_redeteccao


def _jogos(*nomes):
    return [
        JogoSeed(nome=nome, aliases=[nome.lower()], genero="", fit_inicial=5.0)
        for nome in (nomes or ("Roblox",))
    ]


def _salvar(caminho, **campos):
    base = dict(
        video_id="V1",
        titulo="titulo qualquer",
        url="https://y/V1",
        data_publicacao="2026-06-01",
        jogo_detectado="",
        confianca_jogo="nao_detectado",
        fonte_deteccao="nao_detectado",
        views=1000,
        likes=10,
        comentarios=2,
        descricao="",
        tags=[],
    )
    base.update(campos)
    salvar_meu_video(caminho, MeuVideo(**base), data_coleta="2026-07-26")


def _linha(caminho, video_id="V1"):
    return next(l for l in _ler_linhas(caminho) if l["video_id"] == video_id)


# --- Falso positivo gravado e limpo quando o texto nao sustenta mais ---

def test_remove_deteccao_que_o_metadado_nao_sustenta(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(
        caminho,
        jogo_detectado="JOGOS COM DESCONTO NA NUUVEM",
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        jogo_no_seed=False,
        descricao="Obrigado\n\njogo : \n\nJOGOS COM DESCONTO NA NUUVEM\n",
    )

    resumo, mudancas = aplicar_redeteccao(caminho, _jogos())

    assert resumo["removidos"] == 1
    assert _linha(caminho)["jogo_detectado"] == ""
    assert mudancas[0].acao == "removido"


# --- Nunca rebaixar: comentarios nao estao salvos, entao nao ha como conferi-los ---

def test_preserva_deteccao_vinda_de_comentarios(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(
        caminho,
        jogo_detectado="Roblox",
        confianca_jogo="baixa",
        fonte_deteccao="comentarios",
        descricao="sem nada util aqui",
    )

    resumo, _ = aplicar_redeteccao(caminho, _jogos())

    assert resumo["preservados"] == 1
    assert _linha(caminho)["jogo_detectado"] == "Roblox"
    assert _linha(caminho)["fonte_deteccao"] == "comentarios"


def test_metadado_substitui_deteccao_por_comentarios_quando_acha(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(
        caminho,
        jogo_detectado="Roblox",
        confianca_jogo="baixa",
        fonte_deteccao="comentarios",
        descricao="jogo : Minecraft\n",
    )

    resumo, _ = aplicar_redeteccao(caminho, _jogos("Roblox", "Minecraft"))

    assert resumo["trocados"] == 1
    assert _linha(caminho)["jogo_detectado"] == "Minecraft"
    assert _linha(caminho)["fonte_deteccao"] == "descricao"


# --- Jogo recem-cadastrado no seed passa a valer sem nova coleta ---

def test_jogo_cadastrado_depois_da_coleta_passa_a_contar_no_seed(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(
        caminho,
        jogo_detectado="Lava and Aqua",
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        jogo_no_seed=False,
        status_analise="jogo_pendente_seed",
        descricao="jogo : Lava and Aqua\n",
    )

    aplicar_redeteccao(caminho, _jogos("Lava and Aqua"))

    linha = _linha(caminho)
    assert linha["jogo_no_seed"] == "sim"
    assert linha["status_analise"] == "pendente"


def test_status_escolhido_pela_pessoa_e_preservado(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(
        caminho,
        jogo_detectado="Roblox",
        confianca_jogo="alta",
        fonte_deteccao="descricao",
        status_analise="analisado",
        descricao="jogo : Roblox\n",
    )

    aplicar_redeteccao(caminho, _jogos())

    assert _linha(caminho)["status_analise"] == "analisado"


# --- Redeteccao nao coleta nada: a data da coleta nao pode mudar ---

def test_nao_altera_a_data_de_coleta(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(caminho, descricao="jogo : Roblox\n")

    aplicar_redeteccao(caminho, _jogos())

    linha = _linha(caminho)
    assert linha["jogo_detectado"] == "Roblox"
    assert linha["data_coleta"] == "2026-07-26"


def test_simular_nao_escreve_no_arquivo(tmp_path):
    caminho = tmp_path / "meus_videos.csv"
    _salvar(caminho, descricao="jogo : Roblox\n")
    antes = caminho.read_text(encoding="utf-8")

    resumo, mudancas = aplicar_redeteccao(caminho, _jogos(), simular=True)

    assert resumo["detectados"] == 1
    assert len(mudancas) == 1
    assert caminho.read_text(encoding="utf-8") == antes


# --- CLI ---

def test_comando_redetectar_atualiza_o_csv(tmp_path, monkeypatch, capsys):
    import main

    caminho = tmp_path / "meus_videos.csv"
    _salvar(caminho, descricao="jogo : Roblox\n")
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRoblox,roblox,variado,7\n", encoding="utf-8"
    )
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "MEUS_VIDEOS_CSV", caminho)

    assert main.main(["redetectar_meus_videos"]) == 0

    assert _linha(caminho)["jogo_detectado"] == "Roblox"
    assert "Redeteccao" in capsys.readouterr().out


def test_comando_redetectar_dry_run_nao_escreve(tmp_path, monkeypatch, capsys):
    import main

    caminho = tmp_path / "meus_videos.csv"
    _salvar(caminho, descricao="jogo : Roblox\n")
    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRoblox,roblox,variado,7\n", encoding="utf-8"
    )
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "MEUS_VIDEOS_CSV", caminho)
    antes = caminho.read_text(encoding="utf-8")

    assert main.main(["redetectar_meus_videos", "--dry-run"]) == 0

    assert caminho.read_text(encoding="utf-8") == antes
    assert "nada foi salvo" in capsys.readouterr().out.lower()
