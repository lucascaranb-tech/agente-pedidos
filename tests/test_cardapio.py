from src.cardapio import brl, buscar, carregar_cardapio, normalizar


def test_cardapio_carrega_e_ids_sao_unicos():
    itens = carregar_cardapio()
    assert len(itens) == 19
    assert len({i.id for i in itens}) == len(itens)


def test_normalizar_remove_acento_e_hifen():
    assert normalizar("  X-Burguer ") == "x burguer"
    assert normalizar("Água sem Gás") == "agua sem gas"


def test_brl_formata_centavos():
    assert brl(2490) == "R$ 24,90"
    assert brl(123456) == "R$ 1.234,56"
    assert brl(5) == "R$ 0,05"


def test_nome_exato_nao_confunde_com_item_parecido():
    assert [i.id for i in buscar("X-Burguer")] == ["xburguer"]
    assert [i.id for i in buscar("x burguer duplo")] == ["xburguer_duplo"]


def test_termo_ambiguo_devolve_varias_opcoes():
    assert {i.id for i in buscar("coca")} == {"coca_lata", "coca_zero_lata"}
    assert {i.id for i in buscar("batata")} == {"batata_pequena", "batata_grande"}


def test_busca_por_restricao_alimentar():
    ids = {i.id for i in buscar("vegetariano")}
    assert "veggie" in ids and "xburguer" not in ids


def test_busca_sem_resultado():
    assert buscar("pizza") == []
    assert buscar("   ") == []
