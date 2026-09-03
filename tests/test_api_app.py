import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from api.main import app


def test_app_sobe_e_expoe_openapi():
    client = TestClient(app)
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
