import csv
from pathlib import Path

from leitor_csv import _ler_linhas, _separar_aliases


CAMPOS_JOGO = ["nome", "aliases", "genero", "fit_inicial"]


class JogoNaoEncontradoError(ValueError):
    pass


class JogoDuplicadoError(ValueError):
    pass


# Cadastra um jogo novo no jogos_seed.csv. Sem isto so existia adicionar_alias, que exige
# o jogo ja existir — nao havia como criar o primeiro registro. Importa porque a deteccao
# so percorre o seed: jogo ausente dali e invisivel para o sistema inteiro, por mais que
# apareca na descricao dos videos. Recusa nome ou alias que ja seja termo de outro jogo,
# senao o mesmo texto apontaria para dois jogos e a deteccao viraria loteria.
def adicionar_jogo_seed(
    caminho: str | Path,
    nome: str,
    aliases: list[str] | None = None,
    genero: str = "",
    fit_inicial: float = 5.0,
) -> None:
    caminho = Path(caminho)
    nome = nome.strip()
    if not nome:
        raise ValueError("O nome do jogo nao pode ser vazio.")

    # O proprio nome vira alias quando nenhum e informado: sem termo nenhum o jogo entra
    # no seed mas continua indetectavel, que e exatamente o problema que queremos resolver.
    # Em minusculas para seguir a convencao do arquivo (a deteccao normaliza de qualquer
    # jeito, mas o CSV e lido por gente). Alias digitado pelo usuario fica como veio.
    aliases = [alias.strip() for alias in (aliases or []) if alias.strip()] or [nome.lower()]

    linhas = _ler_linhas(caminho)
    termos_existentes = _termos_existentes(linhas)
    for termo in [nome, *aliases]:
        if termo.casefold() in termos_existentes:
            raise JogoDuplicadoError(
                f"O termo '{termo}' ja pertence a um jogo do jogos_seed.csv."
            )

    linhas.append(
        {
            "nome": nome,
            "aliases": "|".join(aliases),
            "genero": genero.strip(),
            "fit_inicial": str(fit_inicial),
        }
    )
    _escrever_jogos(caminho, linhas)


# Todos os termos (nome + aliases) ja usados no seed, em casefold, para detectar colisao.
def _termos_existentes(linhas: list[dict[str, str]]) -> set[str]:
    termos = set()
    for linha in linhas:
        nome = linha.get("nome", "").strip()
        if nome:
            termos.add(nome.casefold())
        for alias in _separar_aliases(linha.get("aliases", "")):
            termos.add(alias.casefold())
    return termos


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
