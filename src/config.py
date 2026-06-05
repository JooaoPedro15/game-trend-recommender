import os


# Le a chave da YouTube Data API v3 da variavel de ambiente YOUTUBE_API_KEY.
# Retorna None se a variavel nao existir ou estiver vazia, para nao quebrar
# os comandos que nao usam o YouTube.
def ler_chave_youtube() -> str | None:
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    return chave or None
