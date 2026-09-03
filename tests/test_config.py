import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config
from config import (
    obter_meu_canal_youtube_id,
    obter_youtube_api_key,
    ler_id_canal_proprio,
)


# Le o ID do canal proprio quando a variavel de ambiente esta definida.
def test_le_id_canal_proprio_quando_definido(monkeypatch):
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "UC123")
    assert ler_id_canal_proprio() == "UC123"


# As funcoes padronizadas leem as variaveis de ambiente.
def test_obter_youtube_api_key(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    assert obter_youtube_api_key() == "CHAVE_FAKE"

    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    assert obter_youtube_api_key() is None


def test_obter_meu_canal_youtube_id(monkeypatch):
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "UC999")
    assert obter_meu_canal_youtube_id() == "UC999"

    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)
    assert obter_meu_canal_youtube_id() is None


# Os nomes antigos delegam para as novas funcoes (config centralizado).
def test_nomes_antigos_delegam(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "X")
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "Y")
    assert config.ler_chave_youtube() == obter_youtube_api_key()
    assert config.ler_id_canal_proprio() == obter_meu_canal_youtube_id()


# O config aponta o .env para a raiz do projeto e nao quebra se ele nao existir.
def test_env_path_aponta_para_a_raiz():
    assert config.ENV_PATH == config.BASE_DIR / ".env"
    assert config.BASE_DIR.name == "game-trend-recommender"


# Sem a variavel, retorna None (comandos que precisam dela avisam de forma clara).
def test_id_canal_proprio_none_quando_ausente(monkeypatch):
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)
    assert ler_id_canal_proprio() is None


# Variavel so com espacos conta como vazia e retorna None.
def test_id_canal_proprio_none_quando_vazio(monkeypatch):
    monkeypatch.setenv("MEU_CANAL_YOUTUBE_ID", "   ")
    assert ler_id_canal_proprio() is None


def test_caminhos_de_dados_existem_e_sao_consistentes():
    import config

    assert config.DATA_DIR == config.BASE_DIR / "data"
    assert config.VIDEOS_CSV == config.DATA_DIR / "videos_coletados.csv"
    assert config.MEUS_VIDEOS_CSV == config.DATA_DIR / "meus_videos.csv"
    assert config.HISTORICO_CSV == config.DATA_DIR / "historico_rankings.csv"
    assert config.WATCHLIST_CSV == config.DATA_DIR / "watchlist_jogos.csv"
    assert config.REPORTS_DIR == config.BASE_DIR / "reports"
