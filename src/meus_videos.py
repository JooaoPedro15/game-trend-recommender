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
    "descricao",
    "tags",
    "jogo_detectado",
    "confianca_jogo",
    "fonte_deteccao",
    "motivo_nao_detectado",
    "jogo_no_seed",
    "url",
    "views",
    "likes",
    "comentarios",
    "comentarios_coletados",
    "respostas_coletadas",
    "comentarios_incompletos",
    "tipo_video",
    "duracao_segundos",
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


# Le o cabecalho gravado no arquivo (lista vazia se ele nao existe ou esta vazio).
def _cabecalho_do_csv(caminho: Path) -> list[str]:
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        return next(csv.reader(arquivo), [])


# Colunas de CAMPOS_MEU_VIDEO que faltam no arquivo gravado. O CSV nasceu com menos
# colunas nas primeiras sprints, e o csv.DictReader simplesmente NAO devolve a chave de
# uma coluna ausente — os leitores caem no padrao ("" ou 0) sem ninguem perceber. Ou seja:
# um video coletado antes da coluna existir fica indistinguivel de um video que de fato
# nao tem descricao. Esta funcao torna essa diferenca visivel.
def colunas_faltando(caminho: str | Path) -> list[str]:
    cabecalho = _cabecalho_do_csv(Path(caminho))
    if not cabecalho:
        return []

    return [campo for campo in CAMPOS_MEU_VIDEO if campo not in cabecalho]


# Reescreve o CSV com o cabecalho atual, preservando os dados existentes e deixando as
# colunas novas vazias. Devolve as colunas acrescentadas ([] quando ja estava em dia).
# Nao inventa dado nenhum: descricao e tags continuam vazias ate uma nova coleta buscar
# esses campos na API. A migracao so devolve a capacidade de distinguir "nao coletado"
# de "nao existe" — quem preenche de verdade e o coletar_meu_canal.
def migrar_meus_videos(caminho: str | Path) -> list[str]:
    caminho = Path(caminho)
    faltando = colunas_faltando(caminho)
    if not faltando:
        return []

    _reescrever_csv(caminho, _ler_linhas(caminho))
    return faltando


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
        "descricao": meu_video.descricao,
        "tags": "|".join(meu_video.tags),
        "jogo_detectado": meu_video.jogo_detectado,
        "confianca_jogo": meu_video.confianca_jogo,
        "fonte_deteccao": meu_video.fonte_deteccao,
        "motivo_nao_detectado": meu_video.motivo_nao_detectado,
        "jogo_no_seed": _bool_para_sim_nao(meu_video.jogo_no_seed),
        "url": meu_video.url,
        "views": int(meu_video.views),
        "likes": int(meu_video.likes),
        "comentarios": int(meu_video.comentarios),
        "comentarios_coletados": int(meu_video.comentarios_coletados),
        "respostas_coletadas": int(meu_video.respostas_coletadas),
        "comentarios_incompletos": _bool_para_sim_nao(meu_video.comentarios_incompletos),
        "tipo_video": meu_video.tipo_video,
        "duracao_segundos": int(meu_video.duracao_segundos),
        "score_resultado_real": calcular_score_resultado_real(meu_video),
        "status_analise": meu_video.status_analise,
    }


# Reescreve o CSV inteiro (cabecalho + linhas). O arquivo so tem os meus videos, entao
# reescrever tudo e simples e seguro inclusive para o caso de atualizacao de uma linha.
def _reescrever_csv(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=CAMPOS_MEU_VIDEO, extrasaction="ignore"
        )
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
        descricao=linha.get("descricao", "").strip(),
        tags=_separar_tags(linha.get("tags", "")),
        duracao_segundos=_para_int(linha.get("duracao_segundos"), 0),
        motivo_nao_detectado=linha.get("motivo_nao_detectado", "").strip(),
        jogo_no_seed=_para_bool(linha.get("jogo_no_seed"), True),
        comentarios_incompletos=_para_bool(linha.get("comentarios_incompletos"), False),
        comentarios_coletados=_para_int(linha.get("comentarios_coletados"), 0),
        respostas_coletadas=_para_int(linha.get("respostas_coletadas"), 0),
    )


def _separar_tags(valor: str | None) -> list[str]:
    return [tag.strip() for tag in (valor or "").split("|") if tag.strip()]


def _bool_para_sim_nao(valor: bool) -> str:
    return "sim" if valor else "nao"


def _para_bool(valor: str | None, padrao: bool) -> bool:
    if valor is None or not valor.strip():
        return padrao
    return valor.strip().casefold() in {"sim", "s", "true", "1", "yes"}


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
