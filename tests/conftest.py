import pytest

from src import config
from src import pedido as ped


@pytest.fixture(autouse=True)
def isolar_estado(tmp_path, monkeypatch):
    """Cada teste começa sem pedidos em andamento e grava o CSV numa pasta temporária."""
    ped.PEDIDOS.clear()
    monkeypatch.setattr(config, "CAMINHO_PEDIDOS", tmp_path / "pedidos_fechados.csv")
    yield
    ped.PEDIDOS.clear()
