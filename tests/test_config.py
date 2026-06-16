import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import ler_id_canal_proprio


# Le o ID do canal proprio quando a variavel de ambiente esta definida.
def test_le_id_canal_proprio_quando_definido(monkeypatch):
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "UC123")
    assert ler_id_canal_proprio() == "UC123"


# Sem a variavel, retorna None (comandos que precisam dela avisam de forma clara).
def test_id_canal_proprio_none_quando_ausente(monkeypatch):
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)
    assert ler_id_canal_proprio() is None


# Variavel so com espacos conta como vazia e retorna None.
def test_id_canal_proprio_none_quando_vazio(monkeypatch):
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "   ")
    assert ler_id_canal_proprio() is None
