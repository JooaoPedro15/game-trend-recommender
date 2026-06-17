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


# Um video do meu proprio canal, ja com o jogo detectado e as metricas reais.
# Representa resultado real do canal (nao referencia de terceiros): foi publicado,
# tem views/likes/comentarios meus. Persistido em data/meus_videos.csv.
# data_coleta e score_resultado_real sao derivados na hora de salvar, por isso ficam
# fora deste dataclass de entrada.
@dataclass
class MeuVideo:
    video_id: str
    titulo: str
    url: str
    data_publicacao: str
    jogo_detectado: str
    confianca_jogo: str
    fonte_deteccao: str
    views: int
    likes: int
    comentarios: int
    tipo_video: str = "desconhecido"
    status_analise: str = "pendente"


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
    # Fit real medido nos meus videos (0-100); None quando o jogo nunca apareceu no
    # meu canal (sem historico, sem ajuste). Veja src/fit_canal.py e o ranker.
    score_fit_real: float | None = None
    # Formato operacional sugerido (curto/longo/live) calibrado pelo meu historico, com
    # fallback para o formato implicito na acao_recomendada; "" quando nenhum aponta um.
    formato_sugerido: str = ""
