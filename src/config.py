import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

RESTAURANTE = os.getenv("RESTAURANTE_NOME", "Burger Lab")
MODELO = os.getenv("MODELO_OPENAI", "gpt-4o-mini")

CAMINHO_CARDAPIO = RAIZ / "data" / "cardapio.json"
CAMINHO_PEDIDOS = RAIZ / "data" / "pedidos_fechados.csv"
CAMINHO_SESSOES = RAIZ / "data" / "sessoes.db"

QTD_MAX_POR_LINHA = 20
