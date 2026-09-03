# Contratos de resposta da API: separados dos dataclasses internos (modelos.py) de
# proposito, para o formato de saida poder ficar estavel mesmo se o interno mudar.

from pydantic import BaseModel, ConfigDict


class _Mirror(BaseModel):
    """Base para schemas que so espelham um dataclass 1:1 (usa from_attributes)."""
    model_config = ConfigDict(from_attributes=True)


# --- ranking / oportunidades -------------------------------------------------

class RankingVideoOut(BaseModel):
    titulo: str
    canal: str
    plataforma: str
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    taxa_engajamento: float
    views_por_dia: float


class RankingItemOut(BaseModel):
    posicao: int
    jogo: str
    score_final: float
    score_tendencia: float
    score_fit_canal: float
    score_fit_real: float | None
    formato_sugerido: str
    score_descoberta: float
    score_saturacao: float
    score_oportunidade: float
    score_evidencia_criadores: float
    score_evidencia_nicho: float
    videos_encontrados: int
    canais_diferentes: int
    motivo: str
    acao_recomendada: str
    videos: list[RankingVideoOut]


class OportunidadeOut(BaseModel):
    posicao: int
    jogo: str
    score_final: float
    score_oportunidade: float
    score_saturacao: float
    acao_recomendada: str
    motivo: str


# --- evidencias ---------------------------------------------------------------

class EvidenciaVideoOut(_Mirror):
    canal: str
    plataforma: str
    tipo_video: str
    titulo: str
    url: str
    views: int
    likes: int
    comentarios: int
    taxa_engajamento: float
    views_por_dia: float
    score_viralidade_video: float
    data_publicacao: str
    nicho: str
    tipo_conteudo: str
    peso_similaridade: float


class EvidenciasJogoOut(BaseModel):
    jogo: str
    score_evidencia: float
    resumo: str
    videos: list[EvidenciaVideoOut]


# --- watchlist ------------------------------------------------------------------

class WatchlistRankingItemOut(BaseModel):
    nome: str
    posicao: int | None
    score_final: float | None
    score_oportunidade: float | None
    acao_recomendada: str | None
    motivo: str | None


# --- diagnostico / qualidade de dados --------------------------------------------

class DiagnosticoOut(_Mirror):
    total: int
    por_plataforma: dict[str, int]
    por_canal: dict[str, int]
    por_origem: dict[str, int]
    sem_data_publicacao: int
    views_zeradas: int
    sem_url: int
    sem_jogo_detectado: int
    jogos_detectados: dict[str, int]


class VideoSemJogoOut(_Mirror):
    titulo: str
    canal: str
    plataforma: str
    views: int
    data_publicacao: str
    url: str
    texto_comentarios: str


class DescobertaOut(_Mirror):
    titulo: str
    canal: str
    url: str
    views: int
    perguntas: int
    candidato: str


# --- meu canal -----------------------------------------------------------------

class MeuVideoSemJogoOut(BaseModel):
    titulo: str
    data_publicacao: str
    views: int
    confianca_jogo: str
    fonte_deteccao: str
    url: str
    sugestao: str


class ComparacaoJogoOut(_Mirror):
    jogo: str
    score_final: float
    score_oportunidade: float
    score_evidencia_nicho: float
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    conclusao: str


class CandidatoRepeticaoOut(_Mirror):
    jogo: str
    melhor_video_titulo: str
    melhor_video_url: str
    score_resultado_real: float
    score_oportunidade: float
    tipo_video: str
    motivo: str


class JogoQueFalhouOut(_Mirror):
    jogo: str
    score_evidencia_nicho: float
    score_oportunidade: float
    score_resultado_real: float
    tipo_video: str
    melhor_video_url: str
    conclusao: str


# --- sistema / historico ---------------------------------------------------------

class StatusOut(_Mirror):
    chave_configurada: bool
    canal_configurado: bool
    videos_coletados: int
    meus_videos: int
    jogos: int
    canais: int
    videos_sem_jogo: int
    tem_relatorios: bool
    tem_historico: bool


class VariacaoJogoOut(_Mirror):
    nome: str
    posicao_anterior: int
    posicao_atual: int
    variacao_score_final: float
    variacao_oportunidade: float


class ComparacaoRankingsOut(_Mirror):
    data_anterior: str
    data_atual: str
    subiram: list[VariacaoJogoOut]
    cairam: list[VariacaoJogoOut]
    estaveis: list[VariacaoJogoOut]
    novos: list[str]
    sumiram: list[str]
