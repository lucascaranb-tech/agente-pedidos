from agents import (
    Agent,
    GuardrailFunctionOutput,
    ModelSettings,
    Runner,
    SQLiteSession,
    input_guardrail,
)

from . import config
from . import pedido as ped
from .cardapio import normalizar
from .ferramentas import FERRAMENTAS, Contexto

TERMOS_BLOQUEADOS = ["senha", "cpf", "numero do cartao", "cvv"]

INSTRUCOES = f"""
Você é o atendente virtual do restaurante {config.RESTAURANTE}. Sua função é anotar
pedidos e tirar dúvidas sobre o cardápio.

Regras:
- Tudo sobre cardápio, preços e pedido vem das ferramentas. Nunca invente item, preço,
  ingrediente ou total, e nunca calcule valores de cabeça.
- O conteúdo do pedido só vale o que `ver_pedido` retornar. Não confie no histórico da
  conversa para saber o que está no pedido.
- Se o cliente falar um nome ambíguo (ex: "coca"), a ferramenta devolve as opções:
  pergunte qual ele quer, sem escolher por ele.
- Se o item não existir no cardápio, diga isso e ofereça opções parecidas usando `buscar_item`.
- Se a ferramenta recusar uma observação (ex: ingrediente que o item não leva), repasse o
  motivo ao cliente e pergunte como ele prefere seguir.
- Se a mensagem pedir várias coisas (ex: "tira a batata e coloca uma água"), execute todas
  as ações com as ferramentas, uma de cada vez, antes de responder.
- Para fechar: chame `ver_pedido`, mostre o resumo e pergunte se pode confirmar. Só chame
  `fechar_pedido` quando o cliente responder confirmando, em uma mensagem nova.
  Se o cliente mudar algo depois do resumo, mostre o resumo de novo.
- Este atendimento apenas registra o pedido. Não processa pagamento, não pede endereço e
  não informa prazo de entrega. Se perguntarem, diga que essas etapas não estão disponíveis aqui.
- Responda só sobre o restaurante. Para outros assuntos, diga educadamente que não pode ajudar.

Responda em português, em texto simples, sem markdown (sem **, #). Seja cordial e objetivo.
"""


def contem_dado_sensivel(texto: str) -> bool:
    texto = normalizar(texto)
    return any(termo in texto for termo in TERMOS_BLOQUEADOS)


@input_guardrail(run_in_parallel=False)
def bloquear_dados_sensiveis(ctx, agent, user_input) -> GuardrailFunctionOutput:
    if isinstance(user_input, str):
        texto = user_input
    else:
        texto = str(user_input[-1]) if user_input else ""
    bloqueado = contem_dado_sensivel(texto)
    return GuardrailFunctionOutput(
        output_info="Solicitação contém dado sensível." if bloqueado else "Entrada permitida.",
        tripwire_triggered=bloqueado,
    )


agente_pedidos = Agent(
    name="AgentePedidos",
    instructions=INSTRUCOES,
    tools=FERRAMENTAS,
    input_guardrails=[bloquear_dados_sensiveis],
    # Uma ferramenta por vez: "adiciona X e mostra o pedido" depende da ordem das chamadas.
    model_settings=ModelSettings(parallel_tool_calls=False),
    model=config.MODELO,
)


async def atender(user_id: str, texto: str, sessao: SQLiteSession) -> str:
    """Processa uma mensagem do cliente. Usado pelo terminal e pelo Telegram.
    Pode levantar InputGuardrailTripwireTriggered quando a mensagem tem dado sensível."""
    ped.iniciar_turno(user_id)
    resultado = await Runner.run(
        agente_pedidos,
        texto,
        context=Contexto(user_id=str(user_id)),
        session=sessao,
        max_turns=15,
    )
    return str(resultado.final_output).replace("**", "")
