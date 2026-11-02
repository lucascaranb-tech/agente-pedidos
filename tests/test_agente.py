import json

from src.agente import agente_pedidos, contem_dado_sensivel
from src.cardapio import carregar_cardapio
from src.config import RAIZ

NOMES_ESPERADOS = {
    "listar_cardapio", "buscar_item", "adicionar_item", "remover_item",
    "ver_pedido", "fechar_pedido", "cancelar_pedido",
}


def test_agente_tem_as_ferramentas_e_o_guardrail():
    assert {t.name for t in agente_pedidos.tools} == NOMES_ESPERADOS
    assert len(agente_pedidos.input_guardrails) == 1


def test_esquema_das_ferramentas_nao_expoe_o_contexto():
    por_nome = {t.name: t for t in agente_pedidos.tools}
    propriedades = por_nome["adicionar_item"].params_json_schema["properties"]
    assert set(propriedades) == {"item", "quantidade", "observacao"}


def test_guardrail_detecta_dados_sensiveis():
    assert contem_dado_sensivel("Qual o CPF cadastrado?")
    assert contem_dado_sensivel("minha SENHA é 1234")
    assert contem_dado_sensivel("o número do cartão é 4111")
    assert not contem_dado_sensivel("Quero um X-Burguer sem cebola")


def test_casos_de_teste_referenciam_itens_validos():
    ids = {i.id for i in carregar_cardapio()}
    casos = json.loads((RAIZ / "tests" / "casos.json").read_text(encoding="utf-8"))
    assert len({c["id"] for c in casos}) == len(casos)
    for caso in casos:
        for item in caso["esperado"].get("itens", []):
            assert item["item"] in ids, f"{caso['id']}: item inexistente {item['item']}"
