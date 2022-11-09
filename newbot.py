"""
Initial code taken from: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
"""
import logging
from telegram import __version__ as TG_VER
from retrieval_algorithms import get_query, clean_query, get_relevant_results, get_results
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]
if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
user_info = {}
FOOD,LOCATION,EXTRA = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Hola! Soy el bot Coco, me gustaría ayudarte a encontrar un lugar para comer :)\nCuéntame, ¿que te gustaría comer?",
    )
    return FOOD

async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_info["food"] = update.message.text
    logger.info(
        "User %s wants to eat: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Genial! ¿Y en que ubicación te gustaría que esté el restaurante?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_info["location"] = update.message.text
    logger.info(
        "User %s requested the place to search: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Entiendo. ¿Hay detalles extras que te gustaría que tenga el restaurante?"
    )
    return EXTRA


async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_info["extra"] = update.message.text if "no" not in update.message.text.lower() else ""
    logger.info(
        "User %s wants as extras: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Muchas gracias :) Voy a buscar los restaurantes que te puedan servir...",
    )
    results = await process_query(user, update)
    if results is None:
        error_message = ("No se encontraron resultados para tu búsqueda :("+
                    "\nSi el error persiste, contacta a mi creador: <a href='https://t.me/danisala03'>Daniel Salazar</a>"+
                    "\nDe lo contrario, inténtalo de nuevo! Escribe /comenzar")
        await update.message.reply_text( 
            error_message, 
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    else:
        print(results)
        message_with_results = "Tus resultados son los siguientes:\n\n"
        for i in range(len(results)):
            if results[i] == None or results[i][1] == None: break # top ended
            message_with_results += "\n<b>"+str((i+1))+"</b>. "+results[i][1]["title"]+": <a href='"+results[i][1]["link"]+"'>Ir al sitio web</a>"
        await update.message.reply_text(
            message_with_results,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Hasta luego! Si quieres volver a hablar puedes escribirme /comenzar :)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def process_query(user, update):
    status, query_or_error = clean_query(user_info["food"].lower(), 
                                        user_info["location"].lower(), 
                                        user_info["extra"].lower())
    if not status:
        logger.info("Query was not generated for user %s as the error: %s occured", user.first_name, query_or_error)
        return None

    # Query cleaned successfully
    logger.info("Query generated for user %s is %s", user.first_name, query_or_error)
    items = get_results(query_or_error, logger, user)
    if items is None:
        logger.info("There were not results found for user %s with query %s", user.first_name, query_or_error)
        return items
    else:
        await update.message.reply_text(
            "Espérame un poco más, aún sigo pensando que podría serte más útil... Podría durar hasta 5 minutos!"
        )
    relevant_results = get_relevant_results(items, query_or_error, logger, user)
    if relevant_results is None or relevant_results[0][1] == 0: # Error and it was never updated as top 1 has 0 weight
        logger.info("There were not relevant results found for user %s with query %s", user.first_name, query_or_error)
        return None
    return relevant_results # top 5 answers

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Hola! Mi propósito es ayudarte a encontrar un restaurante que te pueda gustar. Escribe /comenzar y podremos inciar la conversación."
        +"\n\nVoy a hacerte 3 preguntas breves y esperaré por tus respuestas para buscar resultados relevantes para ti. Como tip, trata de contestar de froma breve y concisa para darte resultados más exactos ;)")

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("5564875729:AAGuKGcYErqLLGD_V-JLlcRNoeAMHf9C-s4").build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("comenzar", start)],
        states={
            FOOD: [MessageHandler(filters.TEXT, food)],
            LOCATION: [
                MessageHandler(filters.TEXT, location),
            ],
            EXTRA: [MessageHandler(filters.TEXT, extra)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    help_handl = CommandHandler('ayuda', help_handler)
    application.add_handler(help_handl)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()