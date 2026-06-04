from collections import Counter
from dataclasses import dataclass

from detector_jogo import detectar_jogos_no_video


@dataclass
class DiagnosticoDados:
    total: int
    por_plataforma: dict[str, int]
    por_canal: dict[str, int]
    sem_data_publicacao: int
    views_zeradas: int
    sem_url: int
    sem_jogo_detectado: int
    jogos_detectados: dict[str, int]


# Gera um diagnostico da qualidade dos videos coletados (funcao pura, sem I/O).
def gerar_diagnostico(videos, jogos) -> DiagnosticoDados:
    jogos_detectados = Counter()
    sem_jogo = 0

    for video in videos:
        encontrados = detectar_jogos_no_video(video, jogos)
        if encontrados:
            for jogo in encontrados:
                jogos_detectados[jogo.nome] += 1
        else:
            sem_jogo += 1

    return DiagnosticoDados(
        total=len(videos),
        por_plataforma=dict(Counter(video.plataforma for video in videos)),
        por_canal=dict(Counter(video.canal for video in videos)),
        sem_data_publicacao=sum(1 for video in videos if not video.data_publicacao.strip()),
        views_zeradas=sum(1 for video in videos if video.views <= 0),
        sem_url=sum(1 for video in videos if not video.url.strip()),
        sem_jogo_detectado=sem_jogo,
        jogos_detectados=dict(jogos_detectados),
    )


# Imprime uma contagem (chave: quantidade) ordenada por chave, ou "(nenhum)" se vazia.
def _imprimir_contagem(contagem: dict[str, int]) -> None:
    if not contagem:
        print("  (nenhum)")
        return
    for chave, quantidade in sorted(contagem.items()):
        print(f"  {chave}: {quantidade}")


# Mostra o diagnostico no terminal, de forma simples e legivel.
def imprimir_diagnostico(diagnostico: DiagnosticoDados) -> None:
    print("=== Diagnostico dos Dados Coletados ===")
    print()
    print(f"Total de videos: {diagnostico.total}")

    print()
    print("Videos por plataforma:")
    _imprimir_contagem(diagnostico.por_plataforma)

    print()
    print("Videos por canal:")
    _imprimir_contagem(diagnostico.por_canal)

    print()
    print("Possiveis problemas:")
    print(f"  Sem data_publicacao: {diagnostico.sem_data_publicacao}")
    print(f"  Views zeradas: {diagnostico.views_zeradas}")
    print(f"  Sem URL: {diagnostico.sem_url}")
    print(f"  Sem jogo detectado: {diagnostico.sem_jogo_detectado}")

    print()
    print("Jogos detectados:")
    if not diagnostico.jogos_detectados:
        print("  (nenhum)")
        return
    for nome, quantidade in sorted(
        diagnostico.jogos_detectados.items(), key=lambda item: (-item[1], item[0])
    ):
        print(f"  {nome}: {quantidade}")


# Retorna os videos sem nenhum jogo detectado, ordenados por views (desc).
def encontrar_videos_sem_jogo(videos, jogos):
    sem_jogo = [video for video in videos if not detectar_jogos_no_video(video, jogos)]
    return sorted(sem_jogo, key=lambda video: video.views, reverse=True)


# Mostra no terminal os videos sem jogo detectado, com os dados uteis para achar o alias faltante.
def imprimir_videos_sem_jogo(videos) -> None:
    print("=== Videos sem jogo detectado ===")
    print()
    if not videos:
        print("Todos os videos foram associados a algum jogo.")
        return

    print(f"Total: {len(videos)}")
    print()
    for video in videos:
        print(f"- {video.titulo}")
        print(f"  Canal: {video.canal} | Plataforma: {video.plataforma} | Views: {video.views}")
        print(f"  Data: {video.data_publicacao} | URL: {video.url}")
        if video.texto_comentarios.strip():
            print(f"  Comentarios: {video.texto_comentarios}")
        print()
