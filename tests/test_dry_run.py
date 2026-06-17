import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main


def _escrever(caminho: Path, linhas: list[str]) -> None:
    caminho.write_text("\n".join(linhas), encoding="utf-8")


# Aponta os caminhos do main para um diretorio temporario e semeia dados minimos com um
# jogo detectavel; remove chave/canal do ambiente (sem rede).
def _preparar(tmp_path, monkeypatch):
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
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("MEU_CANAL_YOUTUBE_ID", raising=False)

    return data_dir, reports_dir


def test_coletar_meu_canal_dry_run_planeja_sem_salvar(tmp_path, monkeypatch, capsys):
    data_dir, _ = _preparar(tmp_path, monkeypatch)

    main.coletar_meu_canal_interativo(10, 20, dry_run=True)

    saida = capsys.readouterr().out
    assert "DRY-RUN" in saida
    assert "22 unidades" in saida  # 2 + 2*10
    assert "nada foi salvo" in saida.lower()
    assert not (data_dir / "meus_videos.csv").exists()


def test_rotina_diaria_dry_run_nao_persiste(tmp_path, monkeypatch, capsys):
    data_dir, reports_dir = _preparar(tmp_path, monkeypatch)

    main.rotina_diaria_interativo(limite=10, limite_comentarios=20, top=5, dry_run=True)

    saida = capsys.readouterr().out
    assert "DRY-RUN" in saida
    assert "nada foi salvo" in saida.lower()
    # nada persistido: nem snapshot, nem CSV do canal, nem relatorios
    assert not (data_dir / "historico_rankings.csv").exists()
    assert not (data_dir / "meus_videos.csv").exists()
    assert not reports_dir.exists() or not list(reports_dir.glob("*.md"))


def test_rotina_diaria_dry_run_via_cli(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)

    assert main.main(["rotina_diaria", "--dry-run", "--top", "3"]) == 0


def test_coletar_meu_canal_dry_run_via_cli(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)

    assert main.main(["coletar_meu_canal", "--limite", "10", "--dry-run"]) == 0
