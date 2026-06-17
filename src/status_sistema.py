# Status geral do sistema (Sprint 10.1): um health-check rapido de "o projeto esta pronto
# para rodar e quais dados ja existem". So leitura — conta linhas dos CSVs e checa
# arquivos/pastas, sem tocar a API nem o ranking. Recebe os booleanos de configuracao ja
# resolvidos (configurada/nao), para nunca ler nem imprimir a chave real.

from dataclasses import dataclass
from pathlib import Path

from diagnostico_dados import encontrar_videos_sem_jogo
from leitor_csv import ler_canais_referencia, ler_jogos_seed, ler_videos_coletados
from meus_videos import ler_meus_videos


# Retrato do estado do sistema: configuracoes e quantidades de dados.
@dataclass
class StatusSistema:
    chave_configurada: bool
    canal_configurado: bool
    videos_coletados: int
    meus_videos: int
    jogos: int
    canais: int
    videos_sem_jogo: int
    tem_relatorios: bool
    tem_historico: bool


# Reune o status a partir dos caminhos dados. Arquivos ausentes contam 0 / False, sem
# quebrar (os leitores ja devolvem lista vazia para arquivo inexistente). chave_configurada
# e canal_configurado vem prontos do chamador (nunca a chave em si).
def coletar_status(
    chave_configurada: bool,
    canal_configurado: bool,
    caminho_videos: str | Path,
    caminho_meus_videos: str | Path,
    caminho_jogos: str | Path,
    caminho_canais: str | Path,
    caminho_historico: str | Path,
    dir_relatorios: str | Path,
) -> StatusSistema:
    videos = ler_videos_coletados(caminho_videos)
    jogos = ler_jogos_seed(caminho_jogos)

    return StatusSistema(
        chave_configurada=chave_configurada,
        canal_configurado=canal_configurado,
        videos_coletados=len(videos),
        meus_videos=len(ler_meus_videos(caminho_meus_videos)),
        jogos=len(jogos),
        canais=len(ler_canais_referencia(caminho_canais)),
        videos_sem_jogo=len(encontrar_videos_sem_jogo(videos, jogos)),
        tem_relatorios=_pasta_tem_arquivos(dir_relatorios),
        tem_historico=_arquivo_com_conteudo(caminho_historico),
    )


# True se o arquivo existe e nao esta vazio.
def _arquivo_com_conteudo(caminho: str | Path) -> bool:
    caminho = Path(caminho)
    return caminho.exists() and caminho.stat().st_size > 0


# True se a pasta existe e tem pelo menos um item dentro.
def _pasta_tem_arquivos(diretorio: str | Path) -> bool:
    diretorio = Path(diretorio)
    return diretorio.is_dir() and any(diretorio.iterdir())


# Texto curto sim/nao para flags booleanas.
def _sim_nao(valor: bool) -> str:
    return "sim" if valor else "nao"


# Mostra o status no terminal, de forma simples e legivel.
def imprimir_status(status: StatusSistema) -> None:
    print("=== Status do Sistema ===")
    print()
    print(f"YOUTUBE_API_KEY: {'configurada' if status.chave_configurada else 'nao configurada'}")
    print(
        f"MEU_CANAL_YOUTUBE_ID: "
        f"{'configurado' if status.canal_configurado else 'nao configurado'}"
    )
    print()
    print(f"Videos coletados (referencia): {status.videos_coletados}")
    print(f"Meus videos (canal proprio): {status.meus_videos}")
    print(f"Jogos no seed: {status.jogos}")
    print(f"Canais de referencia: {status.canais}")
    print(f"Videos sem jogo detectado: {status.videos_sem_jogo}")
    print()
    print(f"Relatorios em reports/: {_sim_nao(status.tem_relatorios)}")
    print(f"Historico de ranking: {_sim_nao(status.tem_historico)}")
