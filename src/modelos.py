from dataclasses import dataclass, field


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
    # A API ja devolve os dois junto com o resto do snippet. Sao a fonte de deteccao mais
    # confiavel de um video de referencia: texto escrito pelo autor, nao por terceiro.
    descricao: str = ""
    tags: list[str] = field(default_factory=list)


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
    # O channelTitle ja vem no mesmo snippet. E o ranker casa os pesos do canal por nome,
    # entao perder esse campo na conversao desliga a calibracao sem avisar.
    canal: str = ""


# Um comentario ja classificado no momento da coleta, para a deteccao decidir o quanto
# confiar nele. Guarda de PROPOSITO apenas o texto e sinais nao identificaveis, seguindo a
# mesma regra de privacidade do coletar_textos_comentarios: nenhum authorChannelId, nome,
# handle ou foto de terceiro entra aqui, e portanto nenhum deles pode vazar para CSV/log.
#
# do_dono: o autor e o dono do canal (authorChannelId == MEU_CANAL_YOUTUBE_ID).
# responde_pergunta_de_jogo: o comentario do topo desta thread perguntava o nome do jogo.
# autor_indice: numero sequencial valido SO dentro deste video, atribuido na ordem em que
#   os autores aparecem. Existe unicamente para contar corroboracao ("duas pessoas
#   diferentes disseram o mesmo nome") sem carregar identidade nenhuma; -1 = desconhecido.
@dataclass
class ComentarioAnalisado:
    texto: str
    do_dono: bool = False
    responde_pergunta_de_jogo: bool = False
    autor_indice: int = -1


@dataclass
class ComentariosColetados:
    textos: list[str] = field(default_factory=list)
    comentarios_principais: int = 0
    respostas: int = 0
    incompleto: bool = False
    analisados: list[ComentarioAnalisado] = field(default_factory=list)


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
    descricao: str = ""
    tags: list[str] = field(default_factory=list)
    duracao_segundos: int = 0
    motivo_nao_detectado: str = ""
    jogo_no_seed: bool = True
    comentarios_incompletos: bool = False
    comentarios_coletados: int = 0
    respostas_coletadas: int = 0


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
