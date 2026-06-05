# Camada de coleta do YouTube.
#
# Esta etapa (Sprint 3.1) define apenas a INTERFACE da coleta — nenhuma requisicao
# real e feita ainda. A implementacao usara a YouTube Data API v3 numa etapa futura,
# com a chave vinda de variavel de ambiente (nunca escrita no codigo).

from modelos import VideoColetado


# Coleta os videos mais recentes de um canal do YouTube e devolve uma lista de
# VideoColetado (plataforma "youtube"). Ainda nao implementado: levanta
# NotImplementedError ate a etapa que liga a YouTube Data API v3.
def coletar_videos_canal(canal_id: str, limite: int) -> list[VideoColetado]:
    raise NotImplementedError(
        "Coleta do YouTube ainda nao implementada. "
        "Sera adicionada em uma etapa futura usando a YouTube Data API v3."
    )
