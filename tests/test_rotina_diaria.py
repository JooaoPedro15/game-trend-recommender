import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main


def _escrever(caminho: Path, linhas: list[str]) -> None:
    caminho.write_text("\n".join(linhas), encoding="utf-8")


# Aponta os caminhos do main para um diretorio temporario e semeia dados minimos com um
# jogo detectavel, para o ranking nao sair vazio.
def _preparar_projeto(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    reports_dir = tmp_path / "reports"

    _escrever(data_dir / "jogos_seed.csv", ["nome,aliases,genero,fit_inicial", "Repo,repo,terror,8"])
    _escrever(
        data_dir / "canais_referencia.csv",
        ["nome,plataforma,url,peso", "Canal,youtube,https://y/c,1.0"],
    )
    _escrever(
        data_dir / "videos_coletados.csv",
        [
            "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,texto_comentarios",
            "Repo viralizou,Canal,youtube,https://y/1,100000,9000,500,2026-05-01,qual o nome do jogo",
        ],
    )

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "VIDEOS_CSV", data_dir / "videos_coletados.csv")
    monkeypatch.setattr(main, "MEUS_VIDEOS_CSV", data_dir / "meus_videos.csv")
    monkeypatch.setattr(main, "HISTORICO_CSV", data_dir / "historico_rankings.csv")
    monkeypatch.setattr(main, "REPORTS_DIR", reports_dir)

    # Sem chave/canal: a coleta (unico passo de rede) e pulada, sem tocar a API.
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)

    return data_dir, reports_dir


def test_rotina_diaria_roda_offline_ponta_a_ponta(tmp_path, monkeypatch, capsys):
    data_dir, reports_dir = _preparar_projeto(tmp_path, monkeypatch)

    main.rotina_diaria_interativo(limite=5, limite_comentarios=10, top=5)

    saida = capsys.readouterr().out
    # coleta pulada (sem rede) e resumo final presente
    assert "Coleta do canal pulada" in saida
    assert "=== Resumo da Rotina ===" in saida
    assert "Videos analisados: 0 (coleta pulada)" in saida
    # passos offline rodaram: snapshot salvo e relatorios gerados
    assert (data_dir / "historico_rankings.csv").exists()
    relatorios = list(reports_dir.glob("*.md"))
    assert len(relatorios) == 2
    assert any(r.name.startswith("ranking_") for r in relatorios)
    assert any(r.name.startswith("calibracao_ranking_") for r in relatorios)


def test_rotina_diaria_passa_pelo_cli(tmp_path, monkeypatch):
    _preparar_projeto(tmp_path, monkeypatch)

    # exercita o parser/dispatch: nao deve levantar e retorna 0
    assert main.main(["rotina_diaria", "--limite", "5", "--comentarios", "10", "--top", "3"]) == 0
