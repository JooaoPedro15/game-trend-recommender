import os
from pathlib import Path


# Carrega o .env da raiz do projeto para as variaveis ficarem disponiveis em os.environ sem
# precisar exportar no shell. O import do python-dotenv e protegido: se o pacote nao estiver
# instalado (ou o .env nao existir), o projeto segue lendo apenas o ambiente ja exportado —
# nada quebra. load_dotenv com um caminho inexistente nao faz nada (so retorna False).
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

# Caminhos de dados compartilhados entre a CLI (main.py) e a API (api/). Ficam aqui
# para nao criar duas fontes de verdade sobre onde os CSVs moram.
DATA_DIR = BASE_DIR / "data"
VIDEOS_CSV = DATA_DIR / "videos_coletados.csv"
MEUS_VIDEOS_CSV = DATA_DIR / "meus_videos.csv"
HISTORICO_CSV = DATA_DIR / "historico_rankings.csv"
WATCHLIST_CSV = DATA_DIR / "watchlist_jogos.csv"
REPORTS_DIR = BASE_DIR / "reports"

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(ENV_PATH, override=True)


# Le a chave da YouTube Data API v3 da variavel de ambiente YOUTUBE_API_KEY.
# Retorna None se nao existir ou estiver vazia, para nao quebrar os comandos offline.
def obter_youtube_api_key() -> str | None:
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    return chave or None


# Le o ID do meu canal principal do YouTube da variavel MEU_CANAL_YOUTUBE_ID.
# Retorna None se nao existir ou estiver vazia, para os comandos do canal proprio poderem
# avisar de forma clara em vez de quebrar.
def obter_meu_canal_youtube_id() -> str | None:
    canal = os.environ.get("MEU_CANAL_YOUTUBE_ID", "").strip()
    return canal or None


# Nomes anteriores, mantidos para compatibilidade com o resto do projeto; delegam para as
# funcoes acima (config centralizado: uma unica fonte de leitura das variaveis de ambiente).
def ler_chave_youtube() -> str | None:
    return obter_youtube_api_key()


def ler_id_canal_proprio() -> str | None:
    return obter_meu_canal_youtube_id()
