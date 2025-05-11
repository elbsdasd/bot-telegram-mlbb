from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import os
from dotenv import load_dotenv
import logging

# Cargar las variables de entorno
load_dotenv()

# Configurar el logging de la aplicación
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener el TOKEN de Telegram desde las variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Comprobación para asegurar que las variables de entorno están configuradas correctamente
if not TOKEN:
    logger.error("La variable de entorno 'TELEGRAM_TOKEN' no está configurada correctamente.")
    raise ValueError("La variable de entorno 'TELEGRAM_TOKEN' no está configurada correctamente.")
if not WEBHOOK_URL:
    logger.error("La variable de entorno 'WEBHOOK_URL' no está configurada correctamente.")
    raise ValueError("La variable de entorno 'WEBHOOK_URL' no está configurada correctamente.")

def main():
    # Crear la aplicación de Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Añadir los manejadores de comandos
    application.add_handler(CommandHandler("start", say_hello))
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_handler(CommandHandler("Video_Tutorial_Texturas", send_video_tutorial))
    application.add_handler(CommandHandler("Inf_Texturas", send_info_texturas))
    application.add_handler(CallbackQueryHandler(handle_buttons))

    # Configurar el webhook
    logger.info("Iniciando el servidor con el webhook en %s", WEBHOOK_URL)
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),  # El puerto puede estar configurado en Heroku como variable de entorno
        webhook_url=WEBHOOK_URL  # La URL, evitando imprimir el token
    )
    
if __name__ == "__main__":
    main()

