"""Bot do Telegram: python -m src.telegram_bot"""
import asyncio
import logging
import os
from collections import defaultdict

from agents import SQLiteSession
from agents.exceptions import InputGuardrailTripwireTriggered
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from . import config
from . import pedido as ped
from .agente import atender

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

MSG_BLOQUEIO = (
    "Por segurança, não posso receber nem informar dados sensíveis como senha, CPF, "
    "número do cartão ou CVV."
)

# Uma mensagem por vez para cada cliente: evita duas execuções mexendo no mesmo pedido.
TRAVAS = defaultdict(asyncio.Lock)


def get_session(user_id: int) -> SQLiteSession:
    config.CAMINHO_SESSOES.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteSession(session_id=f"pedidos_{user_id}", db_path=str(config.CAMINHO_SESSOES))


async def responder_em_partes(message, texto: str) -> None:
    for i in range(0, len(texto), 4000):
        await message.reply_text(texto[i : i + 4000])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name if update.effective_user else "cliente"
    await update.effective_message.reply_text(
        f"Olá, {nome}! Sou o atendente virtual do {config.RESTAURANTE}.\n\n"
        "Posso mostrar o cardápio, anotar seu pedido e tirar dúvidas sobre os itens.\n"
        "Use /help para ver exemplos."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Exemplos:\n"
        "• Quero dois X-Burguer sem cebola e uma coca\n"
        "• Tem opção vegetariana?\n"
        "• Tira a batata e coloca uma água sem gás\n"
        "• Pode fechar o pedido\n\n"
        "Comandos:\n"
        "/cardapio - mostra o cardápio\n"
        "/pedido - mostra o pedido atual\n"
        "/cancelar - esvazia o pedido"
    )


async def cmd_cardapio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder_em_partes(update.effective_message, ped.listar_cardapio(""))


async def cmd_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(ped.texto_pedido(str(update.effective_user.id)))


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with TRAVAS[update.effective_user.id]:
        await update.effective_message.reply_text(ped.limpar_pedido(str(update.effective_user.id)))


async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, user = update.effective_message, update.effective_user
    if msg is None or user is None or not msg.text:
        return

    async with TRAVAS[user.id]:
        await msg.chat.send_action(ChatAction.TYPING)
        try:
            resposta = await atender(str(user.id), msg.text, get_session(user.id))
        except InputGuardrailTripwireTriggered:
            await msg.reply_text(MSG_BLOQUEIO)
            return
        except Exception:
            logging.exception("Erro no agente")
            await msg.reply_text("Tive um problema para processar sua mensagem. Tente novamente em instantes.")
            return

    await responder_em_partes(msg, resposta)


async def erro_telegram(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Erro no Telegram: %s", context.error)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Defina TELEGRAM_BOT_TOKEN no arquivo .env ou no ambiente.")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY no arquivo .env ou no ambiente.")

    # Os pedidos em andamento ficam na memória; apagar as sessões ao iniciar evita o agente
    # "lembrar" de itens de um pedido que não existe mais.
    if config.CAMINHO_SESSOES.exists():
        config.CAMINHO_SESSOES.unlink()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cardapio", cmd_cardapio))
    app.add_handler(CommandHandler("pedido", cmd_pedido))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem))
    app.add_error_handler(erro_telegram)

    print("Bot iniciado. Envie /start no Telegram. Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
