import os
import json
import asyncio
import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

TOKEN = "7834991561:AAEJN4oP0MxJn5K9ShS1qljJ13jSb4BfRXw"
PAYPAL_CLIENT_ID = "ARV1CLPp866P1sLfq85LPeTP-pODgOcKdp1TCUYVSiPeuekLn6J71hKlf9K64ThABV9MKdTCppm3PG9n"
PAYPAL_SECRET = "EEFMps6m46M0Jn3_z5S6bl89AHe6p2euc-fJqez5TDw3Xjgs1JOzjtDGmKlSqM3mcdLw3q3Ey772zquH"
WEBHOOK_URL = "https://bot-telegram-mlbb.onrender.com/webhook"
PAYPAL_API = "https://api-m.paypal.com"
PRECIOS = {"video_tutorial": "1.00"}

pagos_confirmados = set()

# Obtener token OAuth de PayPal
async def obtener_token_paypal():
    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        data = {'grant_type': 'client_credentials'}
        async with session.post(f"{PAYPAL_API}/v1/oauth2/token", auth=auth, data=data) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                return token_data.get("access_token")
            else:
                print("[ERROR] No se pudo obtener token de PayPal")
                return None

# Crear orden de pago
async def crear_pago(usuario_id):
    token = await obtener_token_paypal()
    if not token:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": PRECIOS["video_tutorial"]},
            "custom_id": str(usuario_id)
        }],
        "application_context": {
            "return_url": f"{WEBHOOK_URL}/paypal/success",
            "cancel_url": f"{WEBHOOK_URL}/paypal/cancel",
            "brand_name": "Bot MLBB",
            "user_action": "PAY_NOW"
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PAYPAL_API}/v2/checkout/orders", headers=headers, json=body) as resp:
            data = await resp.json()
            if resp.status == 201:
                for link in data.get("links", []):
                    if link.get("rel") == "approve":
                        return link["href"]
            print("[ERROR] No se pudo crear el pago:", data)
            return None

# Webhook de PayPal
async def handle_webhook(request):
    payload = await request.json()
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})

    if event_type == "CHECKOUT.ORDER.APPROVED":
        order_id = resource.get("id")
        custom_id = resource.get("purchase_units", [{}])[0].get("custom_id")
        token = await obtener_token_paypal()
        if token and order_id and custom_id:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture", headers=headers) as resp:
                    if resp.status == 201:
                        pagos_confirmados.add(int(custom_id))
                        print(f"[✔ PAGO CAPTURADO] Usuario {custom_id}")
    return web.Response(status=200)

# Webhook de Telegram
async def handle_telegram(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(status=200)

# Comandos del bot
async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenido. Usa /menu para ver opciones.")

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Video Tutorial", callback_data="video_tutorial")],
        [InlineKeyboardButton("ℹ Información de Texturas", callback_data="info_texturas")],
        [InlineKeyboardButton("🛠 Activar Desarrollador", callback_data="activar_desarrollador")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Menú:", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "video_tutorial":
        if user_id in pagos_confirmados:
            mensaje = (
                "🎬 Video tutorial:\n"
                "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk\n\n"
                "📺 Solución YouTube:\nhttps://youtu.be/8ZEExAeS4aQ"
            )
            await query.edit_message_text(text=mensaje)
        else:
            url = await crear_pago(user_id)
            if url:
                await query.edit_message_text(f"Paga $1 USD aquí:\n{url}")
            else:
                await query.edit_message_text("❌ Error al generar el pago.")
    elif query.data == "info_texturas":
        msg = (
            "Las texturas (mods) cambian solo la apariencia visual de los héroes en el juego. "
            "No afectan la jugabilidad ni el rendimiento, por lo tanto, no son baneables."
        )
        await query.edit_message_text(text=msg)
    elif query.data == "activar_desarrollador":
        mensaje = (
            "<b>Modo desarrollador:</b>\n"
            "🔍 TikTok 1: https://vm.tiktok.com/ZMSJnGE8F/\n"
            "🔍 TikTok 2: https://vm.tiktok.com/ZMSJncaNf/\n"
            "🔍 TikTok 3: https://vm.tiktok.com/ZMSJn3F2z/\n"
            "🔍 TikTok 4: https://vm.tiktok.com/ZMSJn7EC6/\n"
            "🔍 TikTok 5: https://vm.tiktok.com/ZMSJWRPjP/\n"
            "🔍 TikTok 6: https://vm.tiktok.com/ZMSJWfUNA/"
        )
        await query.edit_message_text(text=mensaje, parse_mode="HTML")

# Iniciar bot y servidor web
async def main():
    global app
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", say_hello))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL + "/webhook")

    info = await app.bot.get_webhook_info()
    print(f"[Webhook Info] {info}")

    # Web server (aiohttp)
    webhook_app = web.Application()
    webhook_app.router.add_post("/webhook", handle_telegram)
    webhook_app.router.add_post("/paypal", handle_webhook)

    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.environ.get("PORT", 8080)))
    await site.start()

    print("Bot corriendo con webhook en Render...")

    # Mantener la app corriendo indefinidamente
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
