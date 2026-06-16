from dataclasses import dataclass


@dataclass
class CanalReferencia:
    nome: str
    plataforma: str
    url: str
    peso: float
    nicho: str = "desconhecido"
    tipo_conteudo: str = "desconhecido"
    peso_similaridade: float = 1.0


@dataclass
class JogoSeed:
    nome: str
    aliases: list[str]
    genero: str
    fit_inicial: float


@dataclass
class VideoColetado:
    titulo: str
    canal: str
    plataforma: str
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    texto_comentarios: str
    origem: str = ""
    tipo_video: str = "desconhecido"


# Detalhes ricos de um video do YouTube (snippet + statistics + contentDetails).
# Estrutura propria porque guarda campos que o VideoColetado nao tem: descricao,
# tags e duracao. Usada na coleta dos meus videos para analise de performance.
@dataclass
class DetalheVideoYoutube:
    video_id: str
    titulo: str
    descricao: str
    tags: list[str]
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    duracao_segundos: int
    tipo_video: str


@dataclass
class ResultadoRecomendacao:
    jogo: JogoSeed
    score_final: float
    score_tendencia: float
    score_fit_canal: float
    score_descoberta: float
    score_saturacao: float
    videos_encontrados: int
    canais_diferentes: int
    motivo: str
    videos: list[VideoColetado]
    score_oportunidade: float = 0.0
    acao_recomendada: str = ""
    score_evidencia_criadores: float = 0.0
    score_evidencia_nicho: float = 0.0
