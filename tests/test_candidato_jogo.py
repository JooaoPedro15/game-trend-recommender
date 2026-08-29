import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from candidato_jogo import candidatos_do_video


def test_template_portugues_um_jogo_chamado():
    achados = candidatos_do_video(
        titulo="Esse caba de calcinha me capturou",
        descricao="nesse vídeo eu trouxe um jogo chamado The lacerator, fui capturado",
    )

    assert "The lacerator" in achados


def test_template_portugues_sem_a_palavra_jogo():
    achados = candidatos_do_video(
        titulo="MEU BARCO NÁUFRAGO NESSA ILHA",
        descricao="nesse vídeo eu trouxe How to fish um game de pescaria, acabei naufragando",
    )

    assert achados  # captura alguma coisa; a cauda some quando o jogo entra no seed
    assert "How to fish" in achados[0]


def test_template_espanhol_en_este_video_jugamos():
    achados = candidatos_do_video(
        titulo="INTENTANDO RESCATAR A UN PINGÜINO",
        descricao="En este video jugamos Super Mario Bros pero no soy mario.",
    )

    assert "Super Mario Bros" in achados


def test_template_espanhol_volvimos_a_jugar():
    achados = candidatos_do_video(
        titulo="ASÍ DEFIENDO EL IMPERIO ROMANO",
        descricao="Volvimos a jugar Shieldwall 🗣️",
    )

    assert "Shieldwall" in achados


def test_conectivo_corta_a_cauda_da_frase():
    # Sem esse corte a captura teria 7 palavras e seria rejeitada, perdendo o nome inteiro.
    achados = candidatos_do_video(
        titulo="EL FREDDY MAS RAPIDO DEL MUNDO",
        descricao="El día de hoy jugamos Hello Neighbor con el mod de fredbear",
    )

    assert "Hello Neighbor" in achados


def test_hashtag_do_titulo_vira_candidato():
    achados = candidatos_do_video(
        titulo="Si te caes pierdes | jugando al barnyard del ps2 👾. #barnyard #plays",
        descricao="",
    )

    assert "barnyard" in achados


def test_hashtag_generica_e_ignorada():
    achados = candidatos_do_video(titulo="Mira nomás como llego 💀. #shorts #clips", descricao="")

    assert achados == []


def test_descricao_vazia_nao_gera_candidato():
    assert candidatos_do_video(titulo="MATAR O VERITY NÃO FOI UMA BOA IDÉIA...", descricao="") == []


def test_link_na_prosa_nao_vira_candidato():
    achados = candidatos_do_video(
        titulo="t", descricao="nesse vídeo eu trouxe https://loja.com/jogo confira"
    )

    assert achados == []


def test_frase_longa_demais_nao_vira_candidato():
    achados = candidatos_do_video(
        titulo="t",
        descricao=(
            "nesse vídeo eu trouxe um monte de coisa que eu queria muito testar faz "
            "tempo e finalmente deu certo hoje"
        ),
    )

    assert achados == []


def test_nao_repete_o_mesmo_candidato():
    achados = candidatos_do_video(
        titulo="jogando barnyard #barnyard",
        descricao="nesse vídeo eu trouxe um jogo chamado barnyard",
    )

    assert achados.count("barnyard") == 1
