"""Conversa pelo terminal, sem Telegram: python -m src.cli"""
import asyncio
import os

from agents import SQLiteSession
from agents.exceptions import InputGuardrailTripwireTriggered

from . import config
from . import pedido as ped
from .agente import atender

MSG_BLOQUEIO = (
    "Por segurança, não posso receber nem informar dados sensíveis como senha, CPF, "
    "número do cartão ou CVV."
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY no arquivo .env ou no ambiente.")

    sessao = SQLiteSession("terminal")
    print(f"{config.RESTAURANTE} - digite 'sair' para encerrar.\n")
    while True:
        texto = input("Você: ").strip()
        if texto.lower() in {"sair", "exit"}:
            break
        if not texto:
            continue
        try:
            print(f"\nAtendente: {await atender('terminal', texto, sessao)}\n")
        except InputGuardrailTripwireTriggered:
            print(f"\nAtendente: {MSG_BLOQUEIO}\n")
        except Exception as erro:
            print(f"\n[erro] {erro!r}\n")

    print("\nEstado final do pedido:\n" + ped.texto_pedido("terminal"))


if __name__ == "__main__":
    asyncio.run(main())
