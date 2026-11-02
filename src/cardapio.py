import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from . import config

ROTULOS_TAGS = {
    "vegetariano": "vegetariano",
    "contem_lactose": "contém lactose",
    "contem_gluten": "contém glúten",
}


@dataclass(frozen=True)
class Item:
    id: str
    nome: str
    categoria: str
    preco_centavos: int
    descricao: str
    tags: tuple
    ingredientes: tuple


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, sem hífen/underscore, sem espaço duplicado."""
    texto = unicodedata.normalize("NFKD", texto.strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("-", " ").replace("_", " ")
    return " ".join(texto.split())


def brl(centavos: int) -> str:
    reais, cent = divmod(abs(centavos), 100)
    texto = f"R$ {reais:,}".replace(",", ".") + f",{cent:02d}"
    return f"-{texto}" if centavos < 0 else texto


@lru_cache(maxsize=1)
def carregar_cardapio() -> tuple:
    with open(config.CAMINHO_CARDAPIO, encoding="utf-8") as arquivo:
        bruto = json.load(arquivo)

    itens = []
    ids_vistos = set()
    for registro in bruto:
        if registro["id"] in ids_vistos:
            raise ValueError(f"ID repetido no cardápio: {registro['id']}")
        if registro["preco"] <= 0:
            raise ValueError(f"Preço inválido para {registro['id']}")
        ids_vistos.add(registro["id"])
        itens.append(
            Item(
                id=registro["id"],
                nome=registro["nome"],
                categoria=registro["categoria"],
                preco_centavos=round(registro["preco"] * 100),
                descricao=registro["descricao"],
                tags=tuple(registro["tags"]),
                ingredientes=tuple(registro["ingredientes"]),
            )
        )
    return tuple(itens)


def categorias() -> list:
    vistas = []
    for item in carregar_cardapio():
        if item.categoria not in vistas:
            vistas.append(item.categoria)
    return vistas


def buscar(termo: str) -> list:
    """Busca por id ou nome exato; senão, cada palavra do termo precisa ser
    prefixo de alguma palavra do nome, da categoria ou das tags do item."""
    t = normalizar(termo)
    if not t:
        return []

    cardapio = carregar_cardapio()
    for item in cardapio:
        if t == normalizar(item.id) or t == normalizar(item.nome):
            return [item]

    palavras_busca = t.split()
    encontrados = []
    for item in cardapio:
        palavras_item = normalizar(" ".join([item.nome, item.categoria, *item.tags])).split()
        if all(any(p.startswith(b) for p in palavras_item) for b in palavras_busca):
            encontrados.append(item)
    return encontrados


def descrever(item: Item) -> str:
    rotulos = [ROTULOS_TAGS[t] for t in item.tags if t in ROTULOS_TAGS]
    sufixo = f" ({', '.join(rotulos)})" if rotulos else ""
    return f"{item.nome} - {brl(item.preco_centavos)}: {item.descricao}{sufixo}"
