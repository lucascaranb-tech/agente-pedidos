"""Regras do pedido em Python puro: nada aqui depende do modelo.
As ferramentas do agente (ferramentas.py) só chamam estas funções."""
import csv
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import config
from .cardapio import Item, brl, buscar, carregar_cardapio, categorias, descrever, normalizar

LOCK = threading.RLock()


@dataclass
class Linha:
    item: Item
    quantidade: int
    observacao: str = ""


@dataclass
class Pedido:
    linhas: list = field(default_factory=list)
    turno_atual: int = 0
    # Turno em que o cliente viu o resumo. None = resumo desatualizado (algo mudou depois).
    turno_resumo: Optional[int] = None

    def total_centavos(self) -> int:
        return sum(l.item.preco_centavos * l.quantidade for l in self.linhas)


PEDIDOS: dict = {}


def obter_pedido(user_id: str) -> Pedido:
    with LOCK:
        return PEDIDOS.setdefault(str(user_id), Pedido())


def iniciar_turno(user_id: str) -> None:
    """Chamar uma vez a cada mensagem do cliente, antes de rodar o agente."""
    with LOCK:
        obter_pedido(user_id).turno_atual += 1


# ---------- busca e validação ----------

def resolver_item(termo: str):
    """Retorna (item, None) se achou exatamente um; senão (None, mensagem)."""
    encontrados = buscar(termo)
    if not encontrados:
        return None, f"Não encontrei '{termo}' no cardápio."
    if len(encontrados) > 1:
        opcoes = "; ".join(f"{i.nome} ({brl(i.preco_centavos)})" for i in encontrados)
        return None, f"Encontrei mais de uma opção para '{termo}': {opcoes}. Pergunte ao cliente qual ele quer."
    return encontrados[0], None


def _ingredientes_removidos(observacao: str) -> list:
    """Trechos 'sem X' da observação (separados por vírgula, ponto e vírgula ou ' e ')."""
    texto = normalizar(observacao)
    trechos = re.split(r"[,;]| e ", texto)
    removidos = []
    for trecho in trechos:
        trecho = trecho.strip()
        if trecho.startswith("sem "):
            removidos.append(trecho[4:].strip())
    return removidos


def validar_observacao(item: Item, observacao: str) -> Optional[str]:
    """Só aceita 'sem X' quando X faz parte dos ingredientes do item.
    Itens sem lista de ingredientes (bebidas) aceitam observação livre."""
    if not item.ingredientes:
        return None
    ingredientes = [normalizar(i) for i in item.ingredientes]
    for removido in _ingredientes_removidos(observacao):
        singular = removido[:-1] if removido.endswith("s") else removido
        if not any(singular in ing for ing in ingredientes):
            return (
                f"{item.nome} não leva '{removido}'. "
                f"Ingredientes: {', '.join(item.ingredientes)}."
            )
    return None


# ---------- texto do pedido ----------

def _nome_linha(linha: Linha) -> str:
    obs = f" ({linha.observacao})" if linha.observacao else ""
    return f"{linha.quantidade}x {linha.item.nome}{obs}"


def texto_pedido(user_id: str) -> str:
    """Resumo do pedido, sem marcar que o cliente o viu."""
    pedido = obter_pedido(user_id)
    if not pedido.linhas:
        return "O pedido está vazio."
    linhas = [
        f"- {_nome_linha(l)}: {brl(l.item.preco_centavos * l.quantidade)}" for l in pedido.linhas
    ]
    return "Pedido atual:\n" + "\n".join(linhas) + f"\nTotal: {brl(pedido.total_centavos())}"


# ---------- operações ----------

def listar_cardapio(categoria: str = "") -> str:
    cardapio = carregar_cardapio()
    if categoria.strip():
        alvo = normalizar(categoria)
        selecionados = [i for i in cardapio if normalizar(i.categoria).startswith(alvo)]
        if not selecionados:
            return f"Categoria '{categoria}' não existe. Categorias: {', '.join(categorias())}."
    else:
        selecionados = list(cardapio)

    blocos = []
    for cat in categorias():
        itens_cat = [i for i in selecionados if i.categoria == cat]
        if itens_cat:
            blocos.append(f"{cat}:\n" + "\n".join(f"- {descrever(i)}" for i in itens_cat))
    return "\n\n".join(blocos)


def buscar_item(termo: str) -> str:
    encontrados = buscar(termo)
    if not encontrados:
        return f"Nada no cardápio corresponde a '{termo}'."
    return "Encontrei:\n" + "\n".join(f"- {descrever(i)}" for i in encontrados)


def adicionar_item(user_id: str, item_termo: str, quantidade: int = 1, observacao: str = "") -> str:
    if quantidade < 1 or quantidade > config.QTD_MAX_POR_LINHA:
        return f"Quantidade inválida: use de 1 a {config.QTD_MAX_POR_LINHA} por item."

    item, erro = resolver_item(item_termo)
    if erro:
        return erro
    erro = validar_observacao(item, observacao)
    if erro:
        return erro

    obs = observacao.strip()
    with LOCK:
        pedido = obter_pedido(user_id)
        existente = next(
            (l for l in pedido.linhas
             if l.item.id == item.id and normalizar(l.observacao) == normalizar(obs)),
            None,
        )
        nova_qtd = (existente.quantidade if existente else 0) + quantidade
        if nova_qtd > config.QTD_MAX_POR_LINHA:
            return f"Limite de {config.QTD_MAX_POR_LINHA} unidades por item. O pedido não foi alterado."

        if existente:
            existente.quantidade = nova_qtd
        else:
            pedido.linhas.append(Linha(item=item, quantidade=quantidade, observacao=obs))
        pedido.turno_resumo = None
        total = pedido.total_centavos()

    adicionado = _nome_linha(Linha(item, quantidade, obs))
    return f"Adicionado: {adicionado}. Total do pedido: {brl(total)}."


def remover_item(user_id: str, item_termo: str, quantidade: Optional[int] = None, observacao: str = "") -> str:
    ids_possiveis = {i.id for i in buscar(item_termo)}
    if not ids_possiveis:
        return f"Não encontrei '{item_termo}' no cardápio."

    with LOCK:
        pedido = obter_pedido(user_id)
        candidatas = [l for l in pedido.linhas if l.item.id in ids_possiveis]
        if observacao.strip():
            candidatas = [l for l in candidatas if normalizar(l.observacao) == normalizar(observacao)]

        if not candidatas:
            return f"'{item_termo}' não está no pedido."
        if len(candidatas) > 1:
            opcoes = "; ".join(_nome_linha(l) for l in candidatas)
            return f"Mais de uma linha corresponde a '{item_termo}': {opcoes}. Pergunte ao cliente qual remover."

        linha = candidatas[0]
        if quantidade is not None and quantidade < 1:
            return "Quantidade inválida para remover."

        if quantidade is None or quantidade >= linha.quantidade:
            pedido.linhas.remove(linha)
            resultado = f"Removido: {_nome_linha(linha)}."
        else:
            linha.quantidade -= quantidade
            resultado = f"Removido {quantidade}x {linha.item.nome}. Restam {linha.quantidade}x."

        pedido.turno_resumo = None
        total = pedido.total_centavos()

    return f"{resultado} Total do pedido: {brl(total)}."


def ver_pedido(user_id: str) -> str:
    """Mostra o pedido e registra que o cliente viu este resumo neste turno."""
    with LOCK:
        pedido = obter_pedido(user_id)
        texto = texto_pedido(user_id)
        if pedido.linhas:
            pedido.turno_resumo = pedido.turno_atual
    return texto


def limpar_pedido(user_id: str) -> str:
    with LOCK:
        PEDIDOS[str(user_id)] = Pedido(turno_atual=obter_pedido(user_id).turno_atual)
    return "Pedido cancelado. O pedido está vazio."


def _proximo_numero() -> int:
    caminho = config.CAMINHO_PEDIDOS
    if not caminho.exists():
        return 1
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return max(sum(1 for _ in csv.reader(arquivo)) - 1, 0) + 1


def fechar_pedido(user_id: str) -> str:
    """Só fecha se o cliente viu o resumo em um turno anterior e nada mudou desde então."""
    with LOCK:
        pedido = obter_pedido(user_id)
        if not pedido.linhas:
            return "Não há itens no pedido para fechar."
        if pedido.turno_resumo is None:
            return "Ainda não dá para fechar: mostre o resumo com ver_pedido e peça a confirmação do cliente."
        if pedido.turno_resumo >= pedido.turno_atual:
            return "O resumo acabou de ser mostrado. Aguarde o cliente confirmar em uma nova mensagem."

        numero = _proximo_numero()
        total = pedido.total_centavos()
        itens = "; ".join(_nome_linha(l) for l in pedido.linhas)

        caminho = config.CAMINHO_PEDIDOS
        caminho.parent.mkdir(parents=True, exist_ok=True)
        novo_arquivo = not caminho.exists()
        with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo)
            if novo_arquivo:
                escritor.writerow(["numero", "data", "user_id", "itens", "total"])
            escritor.writerow([
                numero, datetime.now().isoformat(timespec="seconds"), user_id, itens, f"{total / 100:.2f}",
            ])

        PEDIDOS[str(user_id)] = Pedido(turno_atual=pedido.turno_atual)

    return f"Pedido #{numero} confirmado: {itens}. Total: {brl(total)}."
