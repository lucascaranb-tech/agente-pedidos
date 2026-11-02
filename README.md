# Agente de pedidos para restaurante

## O que o agente faz
- Atende clientes do restaurante fictício Burger Lab pelo Telegram ou pelo terminal
- Mostra o cardápio completo ou por categoria, com preço e restrições (vegetariano, lactose, glúten)
- Anota pedidos em linguagem natural, com quantidade e observação (ex: "dois X-Burguer sem cebola e uma coca")
- Pergunta ao cliente quando o nome é ambíguo (ex: "coca" pode ser Coca-Cola ou Coca-Cola Zero)
- Recusa observações impossíveis (ex: "sem picles" em um item que não leva picles)
- Trata mensagens com várias ações (ex: "tira a batata e coloca uma água")
- Fecha o pedido somente depois de mostrar o resumo e receber a confirmação do cliente
- Grava os pedidos fechados em `data/pedidos_fechados.csv`
- Bloqueia mensagens com dados sensíveis (senha, CPF, número do cartão, CVV) com um guardrail de entrada

## Tecnologias
- Python 3.10+
- OpenAI Agents SDK, com o modelo `gpt-4o-mini`
- python-telegram-bot
- pytest

## Decisões de projeto
- As regras ficam no código (`src/pedido.py`), não no prompt: existência do item, ambiguidade de nome, ingredientes removíveis, limite de quantidade, total do pedido e confirmação
- O modelo só interpreta a mensagem do cliente e escolhe a ferramenta a chamar
- A confirmação é imposta no código: `ver_pedido` registra o turno em que o cliente viu o resumo, e `fechar_pedido` recusa se o resumo não foi mostrado, se foi no mesmo turno ou se o pedido mudou depois dele
- As ferramentas rodam uma por vez (`parallel_tool_calls=False`), porque ações como "adiciona X e mostra o pedido" dependem da ordem
- A função `atender()` em `src/agente.py` é usada pelo terminal e pelo Telegram

## Exemplo de conversa
<!-- Cole aqui o print da conversa no Telegram -->

## Estrutura
```
agente-pedidos/
├── data/
│   └── cardapio.json        # 19 itens em 4 categorias
├── src/
│   ├── config.py            # variáveis de ambiente e caminhos
│   ├── cardapio.py          # carga do cardápio e busca de itens
│   ├── pedido.py            # estado do pedido e regras de negócio
│   ├── ferramentas.py       # ferramentas do agente (function_tool)
│   ├── agente.py            # instruções, guardrail e função atender()
│   ├── cli.py               # conversa pelo terminal
│   └── telegram_bot.py      # bot do Telegram
├── tests/
│   ├── test_cardapio.py
│   ├── test_pedido.py
│   ├── test_agente.py
│   └── casos.json           # cenários de conversa com o resultado esperado
├── .env.example
├── requirements.txt
└── README.md
```

## Como rodar

### Instalação
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

### Chaves no arquivo .env
- `OPENAI_API_KEY`: chave da API da OpenAI
- `TELEGRAM_BOT_TOKEN`: token criado no BotFather (só para o bot)

### Terminal
```bash
python -m src.cli
```

### Telegram
```bash
python -m src.telegram_bot
```

### Comandos do bot
- `/start`
- `/help`
- `/cardapio`
- `/pedido`
- `/cancelar`

## Testes
- Rodam sem chamar a API
- Cobrem busca no cardápio, regras do pedido, ferramentas do agente e guardrail
- `tests/casos.json` reúne cenários de conversa com o resultado esperado, para avaliar o agente com o modelo

```bash
pytest
```

## Limitações
- O pedido em andamento fica na memória: reiniciar o bot esvazia os pedidos abertos
- As sessões de conversa são apagadas quando o bot inicia
- Não há pagamento, endereço nem prazo de entrega
- O cardápio é um arquivo estático, sem controle de estoque
- O guardrail procura palavras-chave, então também bloqueia mensagens legítimas que citem "CPF" ou "senha"
