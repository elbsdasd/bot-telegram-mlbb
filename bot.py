import os
import json
import asyncio
import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "7834991561:AAFYaeSkdCV6C8jJEX81ABcbLqiCKbGHv-w"
PAYPAL_CLIENT_ID = "Aaenpkty_pmWsrzsR8Tr3eQ4HBgHG21RGZ0PoULy2PBfEHxObXXaB_kpMVJeaQq-9zuZrPKWcy9PA"
PAYPAL_SECRET = "EIh7jyA13zoVmjWKntONVB0pc02t6vK2g3-6tACrE582S-Ff7DfyExGxxtEoKmXPWNXofcGXmHDPh6l8"
WEBHOOK_URL = "https://bot-telegram-mlbb.onrender.com/webhook"
PAYPAL_API = "https://api-m.paypal.com"
PRECIOS = {"video_tutorial": "1.00"}

pagos_confirmados = set()

async def obtener_token_paypal():
    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        data = {'grant_type': 'client_credentials'}
        async with session.post(f"{PAYPAL_API}/v1/oauth2/token", auth=auth, data=data) as resp:
            token_data = await resp.json()
            return token_data.get("access_token")

async def crear_pago(usuario_id):
    access_token = await obtener_token_paypal()
    if not access_token:
        print("[ERROR] No se pudo obtener el token de PayPal")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": PRECIOS["video_tutorial"]},
            "custom_id": str(usuario_id)
        }],
        "application_context": {
            "brand_name": "Bot MLBB",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "return_url": f"{WEBHOOK_URL}/success",
            "cancel_url": f"{WEBHOOK_URL}/cancel"
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{PAYPAL_API}/v2/checkout/orders", headers=headers, json=body) as resp:
            data = await resp.json()
            print(f"[PAYPAL RESPONSE] status: {resp.status} - {json.dumps(data, indent=2)}")

            if resp.status != 201:
                print("[ERROR] No se pudo crear el pedido PayPal.")
                return None

            for link in data.get("links", []):
                if link.get("rel") == "approve":
                    return link.get("href")
            return None

async def handle_webhook(request):
    payload = await request.json()
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})

    if event_type == "CHECKOUT.ORDER.APPROVED":
        order_id = resource.get("id")
        custom_id = resource.get("purchase_units", [{}])[0].get("custom_id")
        access_token = await obtener_token_paypal()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture", headers=headers) as resp:
                data = await resp.json()
                if resp.status == 201 and custom_id:
                    pagos_confirmados.add(int(custom_id))
                    print(f"[PAGO CONFIRMADO] Usuario: {custom_id}")

    return web.Response(status=200)

async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenido, presiona /menu para ver las opciones disponibles.")

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Video Tutorial", callback_data="video_tutorial")],
        [InlineKeyboardButton("ℹ Información de Texturas", callback_data="info_texturas")],
        [InlineKeyboardButton("🛠 Activar Desarrollador", callback_data="activar_desarrollador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Menú de opciones:", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    usuario_id = query.from_user.id

    if query.data == "video_tutorial":
        if usuario_id in pagos_confirmados:
            mensaje = (
                "Aquí tienes el video tutorial sobre texturas:\n"
                "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk\n\n"
                "📽 <b>Solución Shizuku (YouTube):</b>\nhttps://youtu.be/8ZEExAeS4aQ?si=LTw4l8GFuSTTZ_bM"
            )
            await query.edit_message_text(text=mensaje, parse_mode="HTML")
        else:
            url_pago = await crear_pago(usuario_id)
            if url_pago:
                await query.edit_message_text(f"Paga $1 USD aquí:\n{url_pago}")
            else:
                await query.edit_message_text("❌ Error al generar el pago. Intenta de nuevo más tarde.")

    elif query.data == "info_texturas":
        mensaje = (
            "Las texturas, mejor conocidas como mods, existen en muchos juegos como Free Fire, Dota 2 y muchos más. "
            "Estos mods no son baneables, ya que no alteran el juego; solo cambian la apariencia básica (por defecto) del héroe, "
            "y solo tú puedes ver los cambios. De esta manera, este mod no afecta el rendimiento de otros jugadores."
        )
        await query.edit_message_text(text=mensaje)
        video_path = "info_texturas.mp4"
        if os.path.exists(video_path):
            with open(video_path, "rb") as f:
                await query.message.reply_video(video=f, caption="Video de ejemplo.")
        else:
            await query.message.reply_text("El archivo de video no fue encontrado.")

    elif query.data == "activar_desarrollador":
        mensaje = (
            "<b>Aquí puedes buscar cómo activar el modo desarrollador para varias marcas:</b>\n\n"
            "🔍 TikTok 1: https://vm.tiktok.com/ZMSJnGE8F/\n"
            "🔍 TikTok 2: https://vm.tiktok.com/ZMSJncaNf/\n"
            "🔍 TikTok 3: https://vm.tiktok.com/ZMSJno3YP/\n"
            "🔍 TikTok 4: https://vm.tiktok.com/ZMSJn7EC6/\n"
            "🔍 TikTok 5: https://vm.tiktok.com/ZMSJWRPjP/\n"
            "🔍 TikTok 6: https://vm.tiktok.com/ZMSJWfUNA/"
        )
        await query.edit_message_text(text=mensaje, parse_mode="HTML")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", say_hello))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    await app.initialize()
    await app.start()
    await app.bot.set_webhook(WEBHOOK_URL)
    print("Webhook de Telegram establecido")

    webhook_app = web.Application()
    webhook_app.router.add_post("/webhook", handle_webhook)

    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    print("Servidor web iniciado")

    await asyncio.Event().wait()  # Mantener activo

if __name__ == "__main__":
    asyncio.run(main())


