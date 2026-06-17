import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modelos import JogoSeed, MeuVideo, ResultadoRecomendacao
from relatorio_calibracao import gerar_relatorio_calibracao_markdown


def _rec(nome, score_final, oportunidade, saturacao, nicho, fit_real):
    return ResultadoRecomendacao(
        jogo=JogoSeed(nome=nome, aliases=[], genero="terror", fit_inicial=8.0),
        score_final=score_final,
        score_tendencia=0.0,
        score_fit_canal=0.0,
        score_descoberta=0.0,
        score_saturacao=saturacao,
        videos_encontrados=0,
        canais_diferentes=0,
        motivo="",
        videos=[],
        score_oportunidade=oportunidade,
        score_evidencia_nicho=nicho,
        score_fit_real=fit_real,
    )


# Meu video fake com data antiga: score_resultado_real deterministico. forte ~66, fraco ~4,
# medio ~51.
def _meu(jogo, video_id, views, likes, comentarios, tipo="curto"):
    return MeuVideo(
        video_id=video_id,
        titulo=f"video {video_id}",
        url=f"https://youtu.be/{video_id}",
        data_publicacao="2020-01-01",
        jogo_detectado=jogo,
        confianca_jogo="media",
        fonte_deteccao="titulo",
        views=views,
        likes=likes,
        comentarios=comentarios,
        tipo_video=tipo,
    )


def _forte(jogo, vid):
    return _meu(jogo, vid, 900000, 120000, 8000)


def _fraco(jogo, vid):
    return _meu(jogo, vid, 80000, 200, 50)


def _medio(jogo, vid):
    return _meu(jogo, vid, 900000, 44000, 1000)


def _cenario():
    ranking = [
        _rec("Acerto", score_final=80, oportunidade=70, saturacao=75, nicho=70, fit_real=66.0),
        _rec("Falhou", score_final=80, oportunidade=70, saturacao=75, nicho=70, fit_real=4.0),
        _rec("Surpresa", score_final=30, oportunidade=40, saturacao=75, nicho=40, fit_real=66.0),
        _rec("EmTeste", score_final=80, oportunidade=55, saturacao=75, nicho=50, fit_real=51.0),
    ]
    meus = [
        _forte("Acerto", "ac"),
        _fraco("Falhou", "fa"),
        _forte("Surpresa", "su"),
        _medio("EmTeste", "em"),
    ]
    return ranking, meus


def test_relatorio_calibracao_tem_todas_as_secoes_e_classifica(tmp_path):
    caminho = tmp_path / "calibracao.md"
    ranking, meus = _cenario()

    gerar_relatorio_calibracao_markdown(caminho, ranking, meus)

    texto = caminho.read_text(encoding="utf-8")
    # cabecalho e secoes
    assert "# Relatorio de Calibracao do Ranking" in texto
    assert "## Jogos que o sistema acertou" in texto
    assert "## Jogos que prometiam mas nao funcionaram" in texto
    assert "## Jogos que funcionaram melhor que o esperado" in texto
    assert "## Jogos para monitorar" in texto
    assert "## Jogos para repetir" in texto
    assert "## Formatos que funcionam melhor comigo" in texto
    assert "## Fit real dos principais jogos" in texto
    # classificacao correta por veredicto
    acertou = texto.split("## Jogos que o sistema acertou")[1].split("##")[0]
    assert "Acerto" in acertou
    falhou = texto.split("## Jogos que prometiam mas nao funcionaram")[1].split("##")[0]
    assert "Falhou" in falhou
    surpresa = texto.split("## Jogos que funcionaram melhor que o esperado")[1].split("##")[0]
    assert "Surpresa" in surpresa
    monitorar = texto.split("## Jogos para monitorar")[1].split("##")[0]
    assert "EmTeste" in monitorar
    # link do meu video como evidencia
    assert "https://youtu.be/ac" in texto


def test_relatorio_calibracao_repetir_e_fit_real(tmp_path):
    caminho = tmp_path / "calibracao.md"
    ranking, meus = _cenario()

    gerar_relatorio_calibracao_markdown(caminho, ranking, meus)

    texto = caminho.read_text(encoding="utf-8")
    # Acerto entra em "repetir" (funcionou + janela aberta); fit real aparece
    repetir = texto.split("## Jogos para repetir")[1].split("##")[0]
    assert "Acerto" in repetir
    fit = texto.split("## Fit real dos principais jogos")[1]
    assert "fit real 66.0" in fit


def test_relatorio_calibracao_vazio(tmp_path):
    caminho = tmp_path / "calibracao_vazio.md"

    gerar_relatorio_calibracao_markdown(caminho, [], [])

    texto = caminho.read_text(encoding="utf-8")
    assert "# Relatorio de Calibracao do Ranking" in texto
    assert "Jogos no ranking: 0" in texto
    assert "(nenhum)" in texto
