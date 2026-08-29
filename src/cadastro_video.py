import csv
from pathlib import Path

from leitor_csv import _ler_linhas, colunas_faltando, ler_videos_coletados, linha_para_video
from modelos import VideoColetado


CAMPOS_VIDEO = [
    "titulo",
    "canal",
    "plataforma",
    "url",
    "views",
    "likes",
    "comentarios",
    "data_publicacao",
    "texto_comentarios",
    "origem",
    "tipo_video",
    "descricao",
    "tags",
]


class VideoDuplicadoError(ValueError):
    pass


# substituir=True troca a linha de mesma URL em vez de recusar. E a valvula de escape do
# cache: sem ela, um video coletado antes das colunas descricao/tags existirem nunca mais e
# visitado, exatamente como aconteceu com as linhas legadas do meus_videos.csv.
def adicionar_video_csv(
    caminho: str | Path, video: VideoColetado, substituir: bool = False
) -> None:
    caminho = Path(caminho)
    _validar_video(video)
    _garantir_csv(caminho)

    alvo = _normalizar_url(video.url)
    nova_linha = _video_para_linha(video)

    if not substituir:
        existentes = ler_videos_coletados(caminho)
        if any(_normalizar_url(existente.url) == alvo for existente in existentes):
            raise VideoDuplicadoError("Ja existe um video cadastrado com essa URL.")

        with caminho.open("a", encoding="utf-8", newline="") as arquivo:
            csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO).writerow(nova_linha)
        return

    linhas = _ler_linhas(caminho)
    for indice, linha in enumerate(linhas):
        if _normalizar_url(linha.get("url", "")) == alvo:
            linhas[indice] = nova_linha
            _reescrever_videos(caminho, linhas)
            return

    linhas.append(nova_linha)
    _reescrever_videos(caminho, linhas)


# Reescreve o CSV inteiro (cabecalho + linhas), do mesmo jeito que o meus_videos.csv faz.
# So e usado no caminho de substituicao: no caminho normal o append e suficiente e evita
# reescrever o arquivo a cada video importado.
def _reescrever_videos(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)


# Importa em lote os videos de um CSV externo para o CSV principal.
# Retorna (importados, duplicados, invalidos); uma linha invalida nao interrompe o lote.
def importar_videos_csv(
    caminho_origem: str | Path, caminho_destino: str | Path
) -> tuple[int, int, int]:
    importados = 0
    duplicados = 0
    invalidos = 0

    for linha in _ler_linhas(caminho_origem):
        try:
            video = linha_para_video(linha)
            video.origem = "importacao"
        except (ValueError, TypeError):
            invalidos += 1
            continue

        try:
            adicionar_video_csv(caminho_destino, video)
            importados += 1
        except VideoDuplicadoError:
            duplicados += 1
        except ValueError:
            invalidos += 1

    return importados, duplicados, invalidos


# Colunas do formato atual que faltam no videos_coletados.csv gravado.
def colunas_faltando_videos(caminho: str | Path) -> list[str]:
    return colunas_faltando(caminho, CAMPOS_VIDEO)


# Reescreve o CSV com o cabecalho atual, preservando as linhas existentes e deixando as
# colunas novas vazias. Devolve as colunas acrescentadas ([] quando ja estava em dia).
# Nao inventa dado: descricao e tags so sao preenchidas por uma nova coleta.
def migrar_videos_coletados(caminho: str | Path) -> list[str]:
    caminho = Path(caminho)
    faltando = colunas_faltando_videos(caminho)
    if not faltando:
        return []

    linhas = _ler_linhas(caminho)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)

    return faltando


def _garantir_csv(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.stat().st_size > 0:
        return

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO)
        escritor.writeheader()


def _validar_video(video: VideoColetado) -> None:
    campos_obrigatorios = {
        "titulo": video.titulo,
        "canal": video.canal,
        "plataforma": video.plataforma,
        "url": video.url,
    }
    faltando = [nome for nome, valor in campos_obrigatorios.items() if not valor.strip()]
    if faltando:
        raise ValueError("Campos obrigatorios vazios: " + ", ".join(faltando))


def _normalizar_url(url: str) -> str:
    return url.strip().casefold()


def _video_para_linha(video: VideoColetado) -> dict[str, str | int]:
    return {
        "titulo": video.titulo,
        "canal": video.canal,
        "plataforma": video.plataforma,
        "url": video.url,
        "views": int(video.views),
        "likes": int(video.likes),
        "comentarios": int(video.comentarios),
        "data_publicacao": video.data_publicacao,
        "texto_comentarios": video.texto_comentarios,
        "origem": video.origem,
        "tipo_video": video.tipo_video,
        "descricao": video.descricao,
        # Mesma convencao do meus_videos.csv: lista separada por barra vertical.
        "tags": "|".join(video.tags),
    }
