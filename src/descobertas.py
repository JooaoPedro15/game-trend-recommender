# Lista de descobertas nao resolvidas: video de referencia em que gente perguntou o nome do
# jogo e nenhum jogo do seed foi identificado. E a saida honesta para o caso que nenhuma
# heuristica resolve — short sem descricao, sem hashtag e sem resposta nos comentarios, onde
# o nome do jogo simplesmente nao existe em texto nenhum.
#
# O sistema nao chuta: devolve o link e deixa a pessoa assistir. Sao 5 videos por semana em
# vez de 220. Funcao pura — recebe os dados ja lidos, nao toca disco nem a API.

from dataclasses import dataclass

from candidato_jogo import candidatos_do_video
from detector_jogo import detectar_jogos_no_video
from modelos import JogoSeed, VideoColetado
from ranker import FRASES_DESCOBERTA, _normalizar_texto


# Um video que atraiu curiosidade e continua sem jogo identificado.
# candidato: nome sugerido pela prosa/hashtag do autor; "" quando nao ha nenhum.
@dataclass
class DescobertaSemJogo:
    titulo: str
    canal: str
    url: str
    views: int
    perguntas: int
    candidato: str


def descobertas_sem_jogo(
    videos: list[VideoColetado], jogos: list[JogoSeed]
) -> list[DescobertaSemJogo]:
    achados = []

    for video in videos:
        if detectar_jogos_no_video(video, jogos):
            continue

        perguntas = _contar_perguntas(video)
        if not perguntas:
            continue

        candidatos = candidatos_do_video(video.titulo, video.descricao)
        achados.append(
            DescobertaSemJogo(
                titulo=video.titulo,
                canal=video.canal,
                url=video.url,
                views=video.views,
                perguntas=perguntas,
                candidato=candidatos[0] if candidatos else "",
            )
        )

    achados.sort(key=lambda descoberta: -descoberta.views)
    return achados


# Reusa as frases que o score de descoberta ja conhece, para a lista e o score partirem do
# mesmo sinal. Duas listas de frases divergiriam na primeira vez que alguem editasse uma.
#
# Nao e uma soma direta de "frase in texto": varias frases da lista sao uma substring de
# outra ("nome do jogo" dentro de "qual o nome do jogo"), entao somar contaria a MESMA
# pergunta duas vezes. Aqui casa as frases da mais longa para a mais curta e descarta um
# casamento que caia inteiro dentro de um trecho ja contado — cada pergunta real do texto
# conta uma vez, nao uma vez por frase da lista que ela contem.
def _contar_perguntas(video: VideoColetado) -> int:
    texto = _normalizar_texto(f"{video.titulo} {video.texto_comentarios}")
    trechos_contados: list[tuple[int, int]] = []

    for frase in sorted(FRASES_DESCOBERTA, key=len, reverse=True):
        posicao = texto.find(frase)
        while posicao != -1:
            fim = posicao + len(frase)
            if not any(inicio <= posicao and fim <= termino for inicio, termino in trechos_contados):
                trechos_contados.append((posicao, fim))
            posicao = texto.find(frase, posicao + 1)

    return len(trechos_contados)


# Mostra a lista no terminal, com o link para a pessoa assistir e decidir.
def imprimir_descobertas(achados: list[DescobertaSemJogo]) -> None:
    print("=== Descobertas sem Jogo Identificado ===")
    print()
    if not achados:
        print("Nenhum video de referencia com sinal de descoberta e sem jogo identificado.")
        return

    print(f"Total: {len(achados)}")
    print()
    for descoberta in achados:
        print(
            f"{descoberta.views:,} views | {descoberta.perguntas} pergunta(s) | "
            f"{descoberta.canal}"
        )
        print(f"  {descoberta.titulo[:70]}")
        print(f"  candidato: {descoberta.candidato or '(nenhum)'}")
        print(f"  {descoberta.url}")
        print()
