import argparse
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import _construir_parser, _data_valida, _fit_valido, _top_valido


# --- --top: apenas inteiros positivos ---

def test_top_valido_aceita_inteiro_positivo():
    assert _top_valido("5") == 5


def test_top_valido_rejeita_zero_negativo_e_nao_inteiro():
    for valor in ["0", "-1", "abc", "3.5"]:
        with pytest.raises(argparse.ArgumentTypeError):
            _top_valido(valor)


# --- --desde: formato YYYY-MM-DD ---

def test_data_valida_aceita_iso():
    assert _data_valida("2026-05-01") == date(2026, 5, 1)


def test_data_valida_rejeita_formato_invalido():
    for valor in ["2026-13-99", "31-12-2026", "abc", "2026/05/01"]:
        with pytest.raises(argparse.ArgumentTypeError):
            _data_valida(valor)


# --- parser: erros saem com exit code 2, sem stack trace ---

def test_parser_top_invalido_sai_com_codigo_2():
    parser = _construir_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["ranking", "--top", "-1"])
    assert excinfo.value.code == 2


def test_parser_formato_invalido_mostra_mensagem_clara(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["exportar_ranking", "--formato", "xml"])
    assert excinfo.value.code == 2
    erro = capsys.readouterr().err
    assert "--formato" in erro
    assert "xml" in erro


def test_parser_desde_invalida_mostra_mensagem_clara(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["ranking", "--desde", "31-12-2026"])
    assert excinfo.value.code == 2
    erro = capsys.readouterr().err
    assert "--desde" in erro
    assert "YYYY-MM-DD" in erro


def test_parser_comando_desconhecido_mostra_mensagem_clara(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["comando_inexistente"])
    assert excinfo.value.code == 2
    erro = capsys.readouterr().err
    assert "invalid choice" in erro


# --- Cada flag erra com o SEU nome (o validador vinha fixo em "--top") ---

def test_erro_de_limite_cita_a_flag_limite(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["coletar_canal_youtube", "UC_X", "--limite", "0"])
    erro = capsys.readouterr().err
    assert "--limite" in erro
    assert "--top" not in erro


# --- 0 desliga a coleta extra de comentarios (o help sempre prometeu isso) ---

def test_comentarios_extra_sem_jogo_aceita_zero():
    parser = _construir_parser()
    args = parser.parse_args(["coletar_meu_canal", "--comentarios-extra-sem-jogo", "0"])
    assert args.comentarios_extra_sem_jogo == 0


def test_comentarios_extra_sem_jogo_rejeita_negativo(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["coletar_meu_canal", "--comentarios-extra-sem-jogo", "-1"])
    assert "--comentarios-extra-sem-jogo" in capsys.readouterr().err


def test_comentarios_continua_exigindo_positivo(capsys):
    parser = _construir_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["coletar_meu_canal", "--comentarios", "0"])
    assert "--comentarios" in capsys.readouterr().err


# --- adicionar_jogo: cadastro do jogo novo no seed ---

def test_parser_aceita_adicionar_jogo_com_opcionais():
    args = _construir_parser().parse_args(
        ["adicionar_jogo", "Lava and Aqua", "--aliases", "lava|aqua", "--genero", "puzzle", "--fit", "6"]
    )

    assert args.comando == "adicionar_jogo"
    assert args.nome == "Lava and Aqua"
    assert args.aliases == "lava|aqua"
    assert args.genero == "puzzle"
    assert args.fit == 6.0


def test_parser_adicionar_jogo_usa_padroes():
    args = _construir_parser().parse_args(["adicionar_jogo", "Apple Worm"])

    assert args.aliases == ""
    assert args.fit == 5.0


def test_fit_valido_aceita_faixa_de_zero_a_dez():
    assert _fit_valido("0") == 0.0
    assert _fit_valido("10") == 10.0
    assert _fit_valido("7.5") == 7.5


def test_fit_valido_rejeita_fora_da_faixa_e_nao_numero():
    for valor in ["-1", "10.1", "abc", ""]:
        with pytest.raises(argparse.ArgumentTypeError):
            _fit_valido(valor)


# --- descobertas_sem_jogo: a fila de trabalho humano ---

def test_parser_aceita_descobertas_sem_jogo():
    args = _construir_parser().parse_args(["descobertas_sem_jogo"])

    assert args.comando == "descobertas_sem_jogo"


def test_comando_descobertas_imprime_a_lista(tmp_path, monkeypatch, capsys):
    import main

    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRoblox,roblox,variado,7\n", encoding="utf-8"
    )
    (tmp_path / "videos_coletados.csv").write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video,descricao,tags\n"
        "MATAR O VERITY,Lozao,youtube,https://y/1,724559,100,10,2026-08-01,"
        "qual o nome do jogo,youtube,curto,,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "VIDEOS_CSV", tmp_path / "videos_coletados.csv")

    assert main.main(["descobertas_sem_jogo"]) == 0

    saida = capsys.readouterr().out
    assert "MATAR O VERITY" in saida
    assert "724,559 views" in saida
    assert "(nenhum)" in saida


# --- --comentarios: liga o score de descoberta, e custa quota ---

def test_parser_coletar_canal_aceita_comentarios():
    args = _construir_parser().parse_args(
        ["coletar_canal_youtube", "UC_X", "--comentarios", "30"]
    )

    assert args.comentarios == 30


def test_parser_coletar_canal_nao_coleta_comentario_por_padrao():
    # Comentario custa 1 unidade de quota por video. O padrao tem que ser nao gastar.
    args = _construir_parser().parse_args(["coletar_canal_youtube", "UC_X"])

    assert args.comentarios == 0


def test_comentarios_chega_ate_o_coletor(tmp_path, monkeypatch):
    import main

    recebido = {}

    def _fake_coletar_canal(channel_id, destino, limite, forcar=False, limite_comentarios=0):
        recebido["limite_comentarios"] = limite_comentarios
        return {"lidos": 0, "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    monkeypatch.setattr(main, "coletar_canal", _fake_coletar_canal)
    monkeypatch.setattr(main, "VIDEOS_CSV", tmp_path / "videos_coletados.csv")

    main.main(["coletar_canal_youtube", "UC_X", "--comentarios", "25"])

    assert recebido["limite_comentarios"] == 25
