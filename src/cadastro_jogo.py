import csv
from pathlib import Path

from leitor_csv import _ler_linhas, _separar_aliases


CAMPOS_JOGO = ["nome", "aliases", "genero", "fit_inicial"]


class JogoNaoEncontradoError(ValueError):
    pass


# Adiciona um alias a um jogo existente no CSV, preservando os demais dados.
# Retorna True se adicionou, False se o alias ja existia; levanta JogoNaoEncontradoError se o jogo nao existe.
def adicionar_alias_jogo(caminho: str | Path, nome_jogo: str, novo_alias: str) -> bool:
    caminho = Path(caminho)
    novo_alias = novo_alias.strip()
    if not novo_alias:
        raise ValueError("O alias nao pode ser vazio.")

    linhas = _ler_linhas(caminho)
    alvo = nome_jogo.strip().casefold()

    for linha in linhas:
        if linha.get("nome", "").strip().casefold() == alvo:
            aliases = _separar_aliases(linha.get("aliases", ""))
            if novo_alias.casefold() in {alias.casefold() for alias in aliases}:
                return False
            aliases.append(novo_alias)
            linha["aliases"] = "|".join(aliases)
            _escrever_jogos(caminho, linhas)
            return True

    raise JogoNaoEncontradoError(f"Jogo nao encontrado: {nome_jogo}")


# Reescreve o CSV de jogos preservando as colunas conhecidas e a ordem das linhas.
def _escrever_jogos(caminho: Path, linhas: list[dict[str, str]]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_JOGO)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({campo: linha.get(campo, "") for campo in CAMPOS_JOGO})
