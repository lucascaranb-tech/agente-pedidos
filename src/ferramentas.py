from dataclasses import dataclass
from typing import Optional

from agents import RunContextWrapper, function_tool

from . import pedido as ped


@dataclass
class Contexto:
    user_id: str


@function_tool
def listar_cardapio(ctx: RunContextWrapper[Contexto], categoria: str = "") -> str:
    """Lista o cardápio com preços e restrições alimentares (vegetariano, lactose, glúten).

    Args:
        categoria: Opcional. Lanches, Acompanhamentos, Bebidas ou Sobremesas. Vazio lista tudo.
    """
    return ped.listar_cardapio(categoria)


@function_tool
def buscar_item(ctx: RunContextWrapper[Contexto], termo: str) -> str:
    """Busca itens do cardápio por nome, categoria ou restrição (ex: 'coca', 'vegetariano', 'batata').

    Args:
        termo: Palavra ou nome do item que o cliente citou.
    """
    return ped.buscar_item(termo)


@function_tool
def adicionar_item(
    ctx: RunContextWrapper[Contexto], item: str, quantidade: int = 1, observacao: str = ""
) -> str:
    """Adiciona um item ao pedido do cliente. Se o nome for ambíguo, a ferramenta devolve as opções.

    Args:
        item: Nome do item como o cliente falou (ex: 'X-Burguer', 'coca zero').
        quantidade: Quantidade de unidades, de 1 a 20.
        observacao: Pedido de alteração, ex: 'sem cebola'. Vazio se não houver.
    """
    return ped.adicionar_item(ctx.context.user_id, item, quantidade, observacao)


@function_tool
def remover_item(
    ctx: RunContextWrapper[Contexto], item: str, quantidade: Optional[int] = None, observacao: str = ""
) -> str:
    """Remove um item do pedido. Sem quantidade, remove a linha inteira.

    Args:
        item: Nome do item que está no pedido.
        quantidade: Quantas unidades remover. Omitir para remover todas.
        observacao: Só se houver duas linhas do mesmo item com observações diferentes.
    """
    return ped.remover_item(ctx.context.user_id, item, quantidade, observacao)


@function_tool
def ver_pedido(ctx: RunContextWrapper[Contexto]) -> str:
    """Mostra os itens e o total do pedido atual. Use sempre antes de pedir a confirmação final."""
    return ped.ver_pedido(ctx.context.user_id)


@function_tool
def fechar_pedido(ctx: RunContextWrapper[Contexto]) -> str:
    """Fecha o pedido. Só chame depois que o cliente confirmar o resumo em uma mensagem nova."""
    return ped.fechar_pedido(ctx.context.user_id)


@function_tool
def cancelar_pedido(ctx: RunContextWrapper[Contexto]) -> str:
    """Esvazia o pedido atual quando o cliente desistir."""
    return ped.limpar_pedido(ctx.context.user_id)


FERRAMENTAS = [
    listar_cardapio,
    buscar_item,
    adicionar_item,
    remover_item,
    ver_pedido,
    fechar_pedido,
    cancelar_pedido,
]
