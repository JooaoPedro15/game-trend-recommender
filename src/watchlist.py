import csv
from datetime import datetime
from pathlib import Path

from leitor_csv import _ler_linhas


CAMPOS_WATCHLIST = ["nome_jogo", "data_adicao"]


# Adiciona um jogo a watchlist. Retorna True se adicionou, False se ele ja estava
# na lista (comparacao ignora maiusculas/minusculas). Levanta ValueError se vazio.
def adicionar_jogo(
    caminho: str | Path, nome_jogo: str, data_adicao: str | None = None
) -> bool:
    caminho = Path(caminho)
    nome_jogo = nome_jogo.strip()
    if not nome_jogo:
        raise ValueError("O nome do jogo nao pode ser vazio.")

    if _esta_na_lista(caminho, nome_jogo):
        return False

    if data_adicao is None:
        data_adicao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    _garantir_cabecalho(caminho)
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_WATCHLIST)
        escritor.writerow({"nome_jogo": nome_jogo, "data_adicao": data_adicao})
    return True


# Retorna os nomes dos jogos na watchlist, na ordem em que foram adicionados.
def listar_jogos(caminho: str | Path) -> list[str]:
    return [linha.get("nome_jogo", "").strip() for linha in _ler_linhas(caminho)]


# Remove um jogo da watchlist (ignora maiusculas/minusculas). Retorna True se
# removeu, False se ele nao estava na lista.
def remover_jogo(caminho: str | Path, nome_jogo: str) -> bool:
    caminho = Path(caminho)
    alvo = nome_jogo.strip().casefold()
    linhas = _ler_linhas(caminho)
    restantes = [
        linha for linha in linhas if linha.get("nome_jogo", "").strip().casefold() != alvo
    ]
    if len(restantes) == len(linhas):
        return False

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_WATCHLIST)
        escritor.writeheader()
        for linha in restantes:
            escritor.writerow({campo: linha.get(campo, "") for campo in CAMPOS_WATCHLIST})
    return True


# Verifica se o jogo ja esta na lista, ignorando maiusculas/minusculas.
def _esta_na_lista(caminho: Path, nome_jogo: str) -> bool:
    alvo = nome_jogo.strip().casefold()
    return any(
        linha.get("nome_jogo", "").strip().casefold() == alvo
        for linha in _ler_linhas(caminho)
    )


# Cria o arquivo com o cabecalho se ele ainda nao existir (ou estiver vazio).
def _garantir_cabecalho(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.stat().st_size > 0:
        return
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_WATCHLIST)
        escritor.writeheader()
