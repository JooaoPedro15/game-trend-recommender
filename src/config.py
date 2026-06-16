import os


# Le a chave da YouTube Data API v3 da variavel de ambiente YOUTUBE_API_KEY.
# Retorna None se a variavel nao existir ou estiver vazia, para nao quebrar
# os comandos que nao usam o YouTube.
def ler_chave_youtube() -> str | None:
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    return chave or None


# Le o ID do meu canal principal do YouTube da variavel de ambiente
# MEU_CANAL_YOUTUBE_ID. Retorna None se a variavel nao existir ou estiver vazia, para os
# comandos que usam o canal proprio poderem avisar de forma clara em vez de quebrar.
def ler_id_canal_proprio() -> str | None:
    canal = os.environ.get("MEU_CANAL_YOUTUBE_ID", "").strip()
    return canal or None
