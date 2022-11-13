"""
Initial code taken from: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
"""
import logging
import os
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
    filename="logs.txt",
    filemode="w"
)
logger = logging.getLogger(__name__)
user_info = {}
FOOD,LOCATION,USER_LOCATION,EXTRA = range(4)
prices = {"0":"Gratis", "1": "Barato", "2": "Moderado", "3":"Caro", "4":"Muy caro"}

""" 
Responds to /comenzar call and starts conversation. Creates the user data in the user_info dict.
"""
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_info[user.id] = {} # { User id : User dict of data }
    await update.message.reply_text(
        "Hola! Soy el bot Coco, me gustaría ayudarte a encontrar un lugar para comer :)\nCuéntame, ¿que te gustaría comer?",
    )
    return FOOD

""" 
Continue the conversation. It saves the food information in user dict.
"""
async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_info[user.id]["food"] = update.message.text
    logger.info(
        "User %s wants to eat: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Genial! ¿Y en que ubicación te gustaría que esté el restaurante?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return LOCATION

""" 
Continue the conversation. It saves the desired location of the restaurants.
"""
async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_info[user.id]["location"] = update.message.text
    logger.info(
        "User %s requested the place to search: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Muy bien. ¿Te gustaria que tu resultados incluyan las direcciones?\n\nDe ser así, por favor toca el ícono de adjuntar, selecciona ubicación y toca enviar mi ubcación actual.\n\nDe lo contrario, respóndeme un No."
    )
    return USER_LOCATION

""" 
Continue the conversation. Receives user location and saved it
"""
async def user_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_location = update.message.location
    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )
    await update.message.reply_text(
        "¡Gracias! Por último, ¿hay detalles extras que te gustaría que tenga el restaurante?"
    )
    user_info[user.id]["user_location"] = user_location
    return EXTRA

""" 
Continue the conversation. It runs only if user didnt share location
"""
async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user
    await update.message.reply_text(
        "Entiendo. Por último, ¿hay detalles extras que te gustaría que tenga el restaurante?"
    )
    user_info[user.id]["user_location"] = None
    return EXTRA

""" 
Continue the conversation. Save extra info of the desired restaurant
"""
async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    if update.message.text.lower() == "si" or update.message.text.lower() == "sí":
        await update.message.reply_text(
        "Perfecto. ¿Cuáles serían?"
        )
        return EXTRA # repeats question
    user_info[user.id]["extra"] = update.message.text if "no" not in update.message.text.lower() else ""
    logger.info(
        "User %s wants as extras: %s", user.first_name, update.message.text
    )
    await update.message.reply_text(
        "Muchas gracias :) Voy a buscar los restaurantes que te puedan servir...",
    )

    # Starts getting the query and getting results
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
        # Results succeeded!

        message_with_results = "Tus resultados son los siguientes:\n\n"
        for i in range(len(results)):
            if results[i] == None or results[i][1] == None: break # top ended as following values are None
            
            # Get price
            price_status, price_level = get_place_property_from_json("No definido", results[i][1], "price_level")
            if price_status: price_level = prices[str(price_level)]
            
            # Get rating
            _, rating = get_place_property_from_json("No definido", results[i][1], "rating")
            
            # Get if its open
            sch_status, is_open = get_place_property_from_json("No definido", results[i][1], "opening_hours")
            if sch_status:
                op_status, is_open = get_place_property_from_json("No definido", is_open, "open_now")
                if op_status: is_open = "Abierto" if is_open else "Cerrado"
            
            # Get location
            location = "No definida"
            if user_info[user.id]["user_location"] != None:
                geo_status, geometry = get_place_property_from_json("No definida", results[i][1], "geometry")
                if geo_status: 
                    loc_status, loc = get_place_property_from_json("No definida", geometry, "location")
                    if loc_status:
                        maps_api = "https://www.google.com/maps/dir/?api=1&origin="+str(user_info[user.id]["user_location"].latitude)+","+str(user_info[user.id]["user_location"].longitude)+"&destination="+str(loc["lat"])+","+str(loc["lng"])
                        location = "<a href='"+maps_api+"'>Ir a la ubicación</a>"
            
            # Save restaurant info to show in the top
            message_with_results +=  ("<b>" + str(i+1) + ")</b>\n<b>Nombre:</b> "+ results[i][1]["name"] + " \n<b>Rating:</b> "
                                        + str(rating) + " \n<b>Categoría de precios:</b> " + price_level + "\n<b>Estado:</b> "
                                        + is_open + "\n<b>Ubicación</b> " + location +"\n\n")

        await update.message.reply_text(
            message_with_results,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    return ConversationHandler.END

""" 
Checks if json result has the property given in param and returns it. If not,
returns the default value given as a param too.
"""
def get_place_property_from_json(default_value, result, json_property):
    try:
        return True, result[json_property]
    except:
        return False, default_value

""" 
Cancel the conversation.
"""
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Hasta luego! Si quieres volver a hablar puedes escribirme /comenzar :)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

""" 
Process the query. Will use the logic of retrieval_algorithms.py
"""
async def process_query(user, update):
    status, query_or_error = clean_query(user_info[user.id]["food"].lower(), 
                                        user_info[user.id]["location"].lower(), 
                                        user_info[user.id]["extra"].lower())
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
            "Espérame un poco más, aún sigo pensando que podría serte más útil... Podría durar hasta 2 minutos!"
        )
    relevant_results = get_relevant_results(items, query_or_error, logger, user)
    if relevant_results is None or relevant_results[0][1] == None: # Error and it was never updated as top 1 has 0 weight
        logger.info("There were not relevant results found for user %s with query %s", user.first_name, query_or_error)
        return None
    return relevant_results # top 5 answers

""" 
Will guide the user on how to use the bot after they call the command /ayuda
"""
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Hola! Mi propósito es ayudarte a encontrar un restaurante que te pueda gustar. Escribe /comenzar y podremos inciar la conversación."
        +"\n\nVoy a hacerte 3 preguntas breves y esperaré por tus respuestas para buscar resultados relevantes para ti. Como tip, trata de contestar de froma breve y concisa para darte resultados más exactos ;)")

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(str(os.getenv('BOT_TOKEN'))).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("comenzar", start)],
        states={
            FOOD: [MessageHandler(filters.TEXT, food)],
            LOCATION: [
                MessageHandler(filters.TEXT, location),
            ],
            USER_LOCATION:  [
                MessageHandler(filters.LOCATION, user_location),
                MessageHandler(filters.TEXT, skip_location),
                CommandHandler("skip", skip_location),
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