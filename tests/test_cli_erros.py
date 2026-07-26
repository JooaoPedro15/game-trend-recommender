import argparse
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import _construir_parser, _data_valida, _top_valido


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
