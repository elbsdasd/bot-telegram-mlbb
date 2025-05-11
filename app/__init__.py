import os
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# API Key del bot de Telegram (guárdala en Heroku como variable de entorno)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# URL de PayPal para los pagos
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

# Configuraciones de Webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Otros valores globales
