import csv

from src import config
from src import pedido as ped

U = "cliente1"


def novo_turno():
    ped.iniciar_turno(U)


def test_adicionar_e_total():
    novo_turno()
    ped.adicionar_item(U, "X-Burguer", 2)
    ped.adicionar_item(U, "coca zero")
    assert ped.obter_pedido(U).total_centavos() == 2 * 2490 + 650
    assert "R$ 56,30" in ped.texto_pedido(U)


def test_mesmo_item_com_mesma_observacao_soma_quantidade():
    ped.adicionar_item(U, "X-Bacon", 1)
    ped.adicionar_item(U, "x bacon", 2)
    linhas = ped.obter_pedido(U).linhas
    assert len(linhas) == 1 and linhas[0].quantidade == 3


def test_observacao_diferente_cria_linha_separada():
    ped.adicionar_item(U, "X-Burguer", 1, "sem cebola")
    ped.adicionar_item(U, "X-Burguer", 1)
    assert len(ped.obter_pedido(U).linhas) == 2


def test_nome_ambiguo_nao_adiciona():
    resposta = ped.adicionar_item(U, "coca")
    assert "mais de uma opção" in resposta
    assert ped.obter_pedido(U).linhas == []


def test_item_inexistente():
    assert "Não encontrei" in ped.adicionar_item(U, "pizza de calabresa")
    assert ped.obter_pedido(U).linhas == []


def test_observacao_com_ingrediente_que_o_item_nao_leva():
    resposta = ped.adicionar_item(U, "X-Burguer", 1, "sem picles")
    assert "não leva" in resposta
    assert ped.obter_pedido(U).linhas == []


def test_observacoes_validas():
    assert "Adicionado" in ped.adicionar_item(U, "X-Burguer", 1, "sem cebola")
    assert "Adicionado" in ped.adicionar_item(U, "X-Salada", 1, "sem cebola e sem tomate")
    assert "Adicionado" in ped.adicionar_item(U, "Coca-Cola Lata", 1, "sem gelo")


def test_limites_de_quantidade():
    assert "inválida" in ped.adicionar_item(U, "X-Burguer", 0)
    assert "inválida" in ped.adicionar_item(U, "X-Burguer", 21)
    ped.adicionar_item(U, "X-Burguer", 20)
    assert "Limite" in ped.adicionar_item(U, "X-Burguer", 1)
    assert ped.obter_pedido(U).linhas[0].quantidade == 20


def test_remover_parcial_e_total():
    ped.adicionar_item(U, "Batata Frita Grande", 3)
    ped.remover_item(U, "batata grande", 1)
    assert ped.obter_pedido(U).linhas[0].quantidade == 2
    ped.remover_item(U, "batata grande")
    assert ped.obter_pedido(U).linhas == []


def test_remover_item_que_nao_esta_no_pedido():
    ped.adicionar_item(U, "X-Burguer")
    assert "não está no pedido" in ped.remover_item(U, "coca zero")


def test_remover_termo_ambiguo_mas_so_um_no_pedido():
    ped.adicionar_item(U, "Coca-Cola Zero Lata")
    ped.adicionar_item(U, "X-Burguer")
    assert "Removido" in ped.remover_item(U, "coca")
    assert [l.item.id for l in ped.obter_pedido(U).linhas] == ["xburguer"]


def test_remover_pede_desambiguacao_quando_ha_duas_linhas():
    ped.adicionar_item(U, "X-Burguer", 1, "sem cebola")
    ped.adicionar_item(U, "X-Burguer", 1)
    assert "Mais de uma linha" in ped.remover_item(U, "X-Burguer")
    assert "Removido" in ped.remover_item(U, "X-Burguer", observacao="sem cebola")


def test_fechar_pedido_vazio():
    assert "Não há itens" in ped.fechar_pedido(U)


def test_nao_fecha_sem_resumo():
    novo_turno()
    ped.adicionar_item(U, "X-Burguer")
    novo_turno()
    assert "mostre o resumo" in ped.fechar_pedido(U)
    assert not config.CAMINHO_PEDIDOS.exists()


def test_nao_fecha_no_mesmo_turno_do_resumo():
    novo_turno()
    ped.adicionar_item(U, "X-Burguer")
    ped.ver_pedido(U)
    assert "nova mensagem" in ped.fechar_pedido(U)
    assert not config.CAMINHO_PEDIDOS.exists()


def test_fecha_apos_confirmacao_em_turno_seguinte():
    novo_turno()
    ped.adicionar_item(U, "X-Burguer", 2, "sem cebola")
    ped.adicionar_item(U, "Coca-Cola Lata")
    ped.ver_pedido(U)
    novo_turno()
    assert "Pedido #1 confirmado" in ped.fechar_pedido(U)
    assert ped.obter_pedido(U).linhas == []

    with open(config.CAMINHO_PEDIDOS, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == 1
    assert linhas[0]["total"] == "56.30"
    assert "2x X-Burguer (sem cebola)" in linhas[0]["itens"]


def test_alteracao_depois_do_resumo_exige_novo_resumo():
    novo_turno()
    ped.adicionar_item(U, "X-Burguer")
    ped.ver_pedido(U)
    novo_turno()
    ped.remover_item(U, "X-Burguer")
    ped.adicionar_item(U, "X-Bacon")
    assert "mostre o resumo" in ped.fechar_pedido(U)


def test_numeracao_sequencial_dos_pedidos():
    for esperado in (1, 2):
        novo_turno()
        ped.adicionar_item(U, "Brownie com Sorvete")
        ped.ver_pedido(U)
        novo_turno()
        assert f"Pedido #{esperado}" in ped.fechar_pedido(U)


def test_pedidos_de_clientes_diferentes_sao_independentes():
    ped.adicionar_item("a", "X-Burguer")
    ped.adicionar_item("b", "Coca-Cola Lata")
    assert [l.item.id for l in ped.obter_pedido("a").linhas] == ["xburguer"]
    assert [l.item.id for l in ped.obter_pedido("b").linhas] == ["coca_lata"]


def test_cancelar_pedido():
    ped.adicionar_item(U, "X-Burguer")
    ped.limpar_pedido(U)
    assert ped.texto_pedido(U) == "O pedido está vazio."


def test_listar_cardapio_por_categoria():
    texto = ped.listar_cardapio("bebidas")
    assert "Coca-Cola Lata" in texto and "X-Burguer" not in texto
    assert "não existe" in ped.listar_cardapio("pizzas")
