import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from status_sistema import coletar_status


def _escrever(caminho: Path, linhas: list[str]) -> None:
    caminho.write_text("\n".join(linhas), encoding="utf-8")


def _cenario_completo(tmp_path: Path) -> dict:
    videos = tmp_path / "videos_coletados.csv"
    _escrever(
        videos,
        [
            "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios",
            "Repo viralizou,Canal,youtube,https://y/1,1000,10,1,2026-05-01,",
            "video aleatorio sem nada,Canal,youtube,https://y/2,1000,10,1,2026-05-01,",
        ],
    )
    meus = tmp_path / "meus_videos.csv"
    _escrever(
        meus,
        [
            "video_id,data_coleta,data_publicacao,titulo,jogo_detectado,confianca_jogo,"
            "fonte_deteccao,url,views,likes,comentarios,tipo_video,score_resultado_real,status_analise",
            "vid1,2026-06-17,2026-06-10,meu video,Repo,alta,descricao,https://y/m1,"
            "1000,10,1,curto,50,pendente",
        ],
    )
    jogos = tmp_path / "jogos_seed.csv"
    _escrever(jogos, ["nome,aliases,genero,fit_inicial", "Repo,repo,terror,8"])

    canais = tmp_path / "canais_referencia.csv"
    _escrever(canais, ["nome,plataforma,url,peso", "Canal,youtube,https://y/c,1.0"])

    historico = tmp_path / "historico_rankings.csv"
    _escrever(historico, ["execucao,nome_jogo,score_final"])

    relatorios = tmp_path / "reports"
    relatorios.mkdir()
    (relatorios / "ranking_2026.md").write_text("x", encoding="utf-8")

    return {
        "caminho_videos": videos,
        "caminho_meus_videos": meus,
        "caminho_jogos": jogos,
        "caminho_canais": canais,
        "caminho_historico": historico,
        "dir_relatorios": relatorios,
    }


def test_status_conta_dados_e_flags(tmp_path):
    caminhos = _cenario_completo(tmp_path)

    status = coletar_status(chave_configurada=True, canal_configurado=False, **caminhos)

    assert status.chave_configurada is True
    assert status.canal_configurado is False
    assert status.videos_coletados == 2
    assert status.videos_sem_jogo == 1  # "video aleatorio" nao casa com nenhum jogo
    assert status.meus_videos == 1
    assert status.jogos == 1
    assert status.canais == 1
    assert status.tem_relatorios is True
    assert status.tem_historico is True


def test_status_arquivos_ausentes_nao_quebram(tmp_path):
    status = coletar_status(
        chave_configurada=False,
        canal_configurado=False,
        caminho_videos=tmp_path / "nao_existe_videos.csv",
        caminho_meus_videos=tmp_path / "nao_existe_meus.csv",
        caminho_jogos=tmp_path / "nao_existe_jogos.csv",
        caminho_canais=tmp_path / "nao_existe_canais.csv",
        caminho_historico=tmp_path / "nao_existe_historico.csv",
        dir_relatorios=tmp_path / "reports_inexistente",
    )

    assert status.videos_coletados == 0
    assert status.meus_videos == 0
    assert status.jogos == 0
    assert status.canais == 0
    assert status.videos_sem_jogo == 0
    assert status.tem_relatorios is False
    assert status.tem_historico is False


def test_historico_vazio_conta_como_sem_historico(tmp_path):
    caminhos = _cenario_completo(tmp_path)
    caminhos["caminho_historico"].write_text("", encoding="utf-8")  # arquivo vazio

    status = coletar_status(chave_configurada=True, canal_configurado=True, **caminhos)

    assert status.tem_historico is False
