import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leitor_csv import ler_canais_referencia


# Garante que as colunas de nicho sao lidas quando existem no CSV.
def test_le_canais_com_colunas_de_nicho(tmp_path):
    caminho = tmp_path / "canais.csv"
    caminho.write_text(
        "nome,plataforma,url,peso,nicho,tipo_conteudo,peso_similaridade\n"
        "Canal A,youtube,https://y/a,1.0,gaming_humor,gameplay,1.3\n",
        encoding="utf-8",
    )

    canais = ler_canais_referencia(caminho)

    assert len(canais) == 1
    canal = canais[0]
    assert canal.nicho == "gaming_humor"
    assert canal.tipo_conteudo == "gameplay"
    assert canal.peso_similaridade == 1.3


# Garante compatibilidade com CSV antigo (sem as colunas novas): usa os valores padrao.
def test_le_canais_sem_colunas_de_nicho_usa_padroes(tmp_path):
    caminho = tmp_path / "canais_antigo.csv"
    caminho.write_text(
        "nome,plataforma,url,peso\n"
        "Canal Antigo,tiktok,https://t/a,1.2\n",
        encoding="utf-8",
    )

    canais = ler_canais_referencia(caminho)

    assert len(canais) == 1
    canal = canais[0]
    assert canal.nicho == "desconhecido"
    assert canal.tipo_conteudo == "desconhecido"
    assert canal.peso_similaridade == 1.0
