import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from comentario_jogo import (
    extrair_nome_do_comentario,
    normalizar_comentario,
    pergunta_nome_do_jogo,
)


# Perguntas COPIADAS de comentarios reais do canal (grafia preservada, inclusive os erros
# de digitacao). Sao elas que autorizam ler a resposta seca da thread como nome de jogo.
PERGUNTAS_REAIS = [
    "Qual é o nome do jogo",
    "Nome do jogo",
    "Nome do jogo?",
    "Nome do game?",
    "Que jogo é esse",
    "Qual nome do jogo?",
    "Fala o nome do jogo para eu",
    "Qual e o nome do jogp",
    "Nome do jogi",
    "Qual o nome do jg",
    "Jogo??",
    "alguem sabe p nome do jogo?",
    "Alguem poderia me enformar o nome do jogo",
    "Onde baixa o jogo",
    "Cuau e o nome do jogo do trem",
    "É qual o nome do jogo\nE se tu falar que tá na descrição no meu não aparece",
]

# Comentarios reais que FALAM de jogo sem perguntar o nome. Sao a maioria esmagadora dos
# comentarios que citam "jogo", e confundi-los com pergunta abriria a porta para qualquer
# frase virar nome de jogo.
NAO_PERGUNTAS_REAIS = [
    "O cara é o jogador daqueles jogos que aparecem em comerciais",
    "Tem de tudo nesse jogo",
    "Pior que o jogo e difícil mesmo kkkk",
    "Já joguei esse jogo, é só seguir e ficar de pozinho",
    "Mas o jogo do Chaos sempre foi usar o especial",
    "Cara nunca jogou algum tenkaichi kkkkkkkk",
    "Eu amava jogar esse jogo no celular.",
    "desista desse jogo vc é ruim demais kkk",
]


def test_reconhece_perguntas_reais_pelo_nome_do_jogo():
    assert [p for p in PERGUNTAS_REAIS if not pergunta_nome_do_jogo(p)] == []


def test_nao_confunde_comentario_sobre_o_jogo_com_pergunta():
    assert [c for c in NAO_PERGUNTAS_REAIS if pergunta_nome_do_jogo(c)] == []


def test_comentario_sem_a_palavra_jogo_nao_e_pergunta():
    assert pergunta_nome_do_jogo("Qual o nome do site?") is False
    assert pergunta_nome_do_jogo("Primeiro") is False


def test_resposta_seca_vira_nome_quando_a_thread_perguntou():
    assert extrair_nome_do_comentario("lava and aqua", aceitar_texto_inteiro=True) == "lava and aqua"


def test_resposta_seca_nao_vira_nome_fora_de_thread_de_pergunta():
    assert extrair_nome_do_comentario("lava and aqua") == ""


def test_corta_o_recado_colado_depois_do_nome():
    texto = "lava and aqua , nao ta na descrição esse 😭😭"

    assert extrair_nome_do_comentario(texto, aceitar_texto_inteiro=True) == "lava and aqua"


def test_extrai_nome_declarado_com_chama():
    assert extrair_nome_do_comentario("chama one line") == "one line"


def test_extrai_nome_declarado_por_terceiro_ignorando_a_mencao():
    texto = "@rubensferreira2257 o nome do jogo é lava and aqua"

    assert extrair_nome_do_comentario(texto) == "lava and aqua"


def test_extrai_nome_declarado_com_rotulo_de_dois_pontos():
    assert extrair_nome_do_comentario("Jogo: Content Warning") == "Content Warning"


# "o jogo e X" ficou de fora dos padroes de declaracao de proposito: pega opiniao.
def test_opiniao_sobre_o_jogo_nao_vira_nome():
    assert extrair_nome_do_comentario("o jogo é muito bom") == ""


def test_pergunta_nunca_vira_resposta():
    assert extrair_nome_do_comentario("Qual é o nome do jogo", aceitar_texto_inteiro=True) == ""


def test_resposta_que_aponta_para_a_descricao_nao_vira_nome():
    for texto in ["ta na descrição", "esta na descricao esse", "link na descrição"]:
        assert extrair_nome_do_comentario(texto, aceitar_texto_inteiro=True) == ""


def test_reacao_curta_do_dono_nao_vira_nome():
    for texto in ["braboo", "sim", "eu msm", "kkkk", "😳", "👀👀👀"]:
        assert extrair_nome_do_comentario(texto, aceitar_texto_inteiro=True) == ""


def test_frase_longa_nao_vira_nome():
    texto = "eu não podia ver isso sozinho desculpa mano foi mal mesmo viu"

    assert extrair_nome_do_comentario(texto, aceitar_texto_inteiro=True) == ""


def test_link_nao_vira_nome():
    texto = "https://www.instagram.com/jootta15"

    assert extrair_nome_do_comentario(texto, aceitar_texto_inteiro=True) == ""


def test_normalizacao_agrupa_grafias_diferentes_do_mesmo_nome():
    assert normalizar_comentario("Lava and Aqua") == normalizar_comentario("lava and aqua!")
    assert normalizar_comentario("R.E.P.O") == "r.e.p.o"
