# Persistencia dos videos do meu proprio canal em data/meus_videos.csv.
#
# - salvar_meu_video: adiciona um video novo ou atualiza o existente (por video_id).
# - calcular_score_resultado_real: pontua o resultado real do video.
# Separado dos videos de referencia (videos_coletados.csv): aqui ficam os MEUS
# resultados, nao a tendencia de terceiros. Nao mexe no ranking principal.

import csv
from datetime import date
from pathlib import Path

from detector_jogo import PADRAO_EXPLICITO
from leitor_csv import _ler_linhas, _para_int
from metricas_video import calcular_score_viralidade_video
from modelos import MeuVideo, VideoColetado


# Colunas do data/meus_videos.csv. data_coleta e score_resultado_real sao calculados
# na hora de salvar; os demais campos vem do MeuVideo.
CAMPOS_MEU_VIDEO = [
    "video_id",
    "data_coleta",
    "data_publicacao",
    "titulo",
    "jogo_detectado",
    "confianca_jogo",
    "fonte_deteccao",
    "url",
    "views",
    "likes",
    "comentarios",
    "tipo_video",
    "score_resultado_real",
    "status_analise",
]


# Pontua de 0 a 100 o resultado real de um video meu reusando a mesma metrica de
# viralidade do resto do sistema (volume + engajamento + velocidade + recencia). Assim
# "resultado real" fica na mesma escala dos scores que o ranking ja conhece, em vez de
# uma formula paralela. Constroi um VideoColetado so para reaproveitar o calculo.
def calcular_score_resultado_real(meu_video: MeuVideo) -> float:
    video = VideoColetado(
        titulo=meu_video.titulo,
        canal="",
        plataforma="youtube",
        url=meu_video.url,
        views=meu_video.views,
        likes=meu_video.likes,
        comentarios=meu_video.comentarios,
        data_publicacao=meu_video.data_publicacao,
        texto_comentarios="",
        origem="meu_canal",
        tipo_video=meu_video.tipo_video,
    )
    return calcular_score_viralidade_video(video)


# Salva um video do meu canal no CSV. Cria o arquivo com cabecalho na primeira vez.
# Se o video_id ainda nao existe, adiciona; se ja existe, atualiza a linha (metricas,
# score e data_coleta), preservando o status_analise ja registrado. Devolve "criado"
# ou "atualizado". data_coleta padrao e hoje (parametrizavel para facilitar os testes).
def salvar_meu_video(
    caminho: str | Path, meu_video: MeuVideo, data_coleta: str | None = None
) -> str:
    caminho = Path(caminho)
    _garantir_csv(caminho)
    data_coleta = data_coleta or date.today().isoformat()

    linhas = _ler_linhas(caminho)
    nova_linha = _meu_video_para_linha(meu_video, data_coleta)

    for indice, linha in enumerate(linhas):
        if linha.get("video_id") == meu_video.video_id:
            nova_linha["status_analise"] = (
                linha.get("status_analise") or meu_video.status_analise
            )
            linhas[indice] = nova_linha
            _reescrever_csv(caminho, linhas)
            return "atualizado"

    linhas.append(nova_linha)
    _reescrever_csv(caminho, linhas)
    return "criado"


# Garante que o CSV existe com o cabecalho (mesmo padrao do cadastro_video).
def _garantir_csv(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.stat().st_size > 0:
        return

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        csv.DictWriter(arquivo, fieldnames=CAMPOS_MEU_VIDEO).writeheader()


# Monta a linha do CSV a partir do MeuVideo, ja com data_coleta e score calculados.
def _meu_video_para_linha(meu_video: MeuVideo, data_coleta: str) -> dict[str, str | int | float]:
    return {
        "video_id": meu_video.video_id,
        "data_coleta": data_coleta,
        "data_publicacao": meu_video.data_publicacao,
        "titulo": meu_video.titulo,
        "jogo_detectado": meu_video.jogo_detectado,
        "confianca_jogo": meu_video.confianca_jogo,
        "fonte_deteccao": meu_video.fonte_deteccao,
        "url": meu_video.url,
        "views": int(meu_video.views),
        "likes": int(meu_video.likes),
        "comentarios": int(meu_video.comentarios),
        "tipo_video": meu_video.tipo_video,
        "score_resultado_real": calcular_score_resultado_real(meu_video),
        "status_analise": meu_video.status_analise,
    }


# Reescreve o CSV inteiro (cabecalho + linhas). O arquivo so tem os meus videos, entao
# reescrever tudo e simples e seguro inclusive para o caso de atualizacao de uma linha.
def _reescrever_csv(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_MEU_VIDEO)
        escritor.writeheader()
        escritor.writerows(linhas)


# Le os meus videos salvos no CSV de volta para objetos MeuVideo. Os campos derivados
# (data_coleta, score_resultado_real) ficam no CSV mas nao no MeuVideo de entrada.
def ler_meus_videos(caminho: str | Path) -> list[MeuVideo]:
    return [_linha_para_meu_video(linha) for linha in _ler_linhas(caminho)]


# Converte uma linha do CSV em MeuVideo (inverso de _meu_video_para_linha).
def _linha_para_meu_video(linha: dict[str, str]) -> MeuVideo:
    return MeuVideo(
        video_id=linha.get("video_id", "").strip(),
        titulo=linha.get("titulo", "").strip(),
        url=linha.get("url", "").strip(),
        data_publicacao=linha.get("data_publicacao", "").strip(),
        jogo_detectado=linha.get("jogo_detectado", "").strip(),
        confianca_jogo=linha.get("confianca_jogo", "").strip(),
        fonte_deteccao=linha.get("fonte_deteccao", "").strip(),
        views=_para_int(linha.get("views"), 0),
        likes=_para_int(linha.get("likes"), 0),
        comentarios=_para_int(linha.get("comentarios"), 0),
        tipo_video=linha.get("tipo_video", "").strip() or "desconhecido",
        status_analise=linha.get("status_analise", "").strip() or "pendente",
    )


# Retorna os meus videos sem jogo detectado (jogo_detectado vazio), ordenados por views
# (desc) para atacar primeiro o buraco que mais custa. Usa a deteccao ja salva no CSV —
# nao re-detecta e nao usa IA.
def listar_meus_videos_sem_jogo(caminho: str | Path) -> list[MeuVideo]:
    sem_jogo = [video for video in ler_meus_videos(caminho) if not video.jogo_detectado.strip()]
    return sorted(sem_jogo, key=lambda video: video.views, reverse=True)


# Sugestao operacional simples (sem IA) para destravar a deteccao de um video: se o titulo
# ja cita o jogo de forma explicita ("Jogo: X"), o que falta e um alias; senao, o caminho
# mais confiavel e marcar "Jogo: Nome" na descricao.
def sugestao_deteccao(titulo: str) -> str:
    if PADRAO_EXPLICITO.search(titulo or ""):
        return "adicionar alias para o jogo citado no titulo"
    return 'usar padrao "Jogo: Nome" na descricao'


# Mostra no terminal os meus videos sem jogo detectado, com os dados uteis e a sugestao.
def imprimir_meus_videos_sem_jogo(videos: list[MeuVideo]) -> None:
    print("=== Meus Videos sem Jogo Detectado ===")
    print()
    if not videos:
        print("Todos os meus videos coletados tem um jogo detectado.")
        return

    print(f"Total: {len(videos)}")
    print()
    for video in videos:
        print(f"- {video.titulo}")
        print(f"  Data: {video.data_publicacao} | Views: {video.views}")
        print(f"  Deteccao: {video.confianca_jogo} (fonte: {video.fonte_deteccao})")
        print(f"  URL: {video.url}")
        print(f"  Sugestao: {sugestao_deteccao(video.titulo)}")
        print()
