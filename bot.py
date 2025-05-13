import os
import json
import asyncio
import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, Application
)
from telegram.constants import ParseMode

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_TOKEN_DE_TELEGRAM_AQUI") # Usa variables de entorno
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "TU_PAYPAL_CLIENT_ID_AQUI")
PAYPAL_SECRET = os.environ.get("PAYPAL_SECRET", "TU_PAYPAL_SECRET_AQUI")
# Esta debe ser la URL base de tu app en Render, ej: https://nombre-app.onrender.com
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "TU_RENDER_WEBHOOK_URL_BASE_AQUI")

PAYPAL_API_BASE_URL = "https://api-m.sandbox.paypal.com" # O "https://api-m.paypal.com" para producción
PRECIO_VIDEO_TUTORIAL = "1.00" # USD

# Enlaces de contenido (mantenlos aquí para fácil acceso)
VIDEO_TUTORIAL_DRIVE_LINK = "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk"
VIDEO_TUTORIAL_YOUTUBE_LINK = "https://youtu.be/8ZEExAeS4aQ"

# --- ESTADO DEL BOT (Considerar persistencia para producción) ---
# ADVERTENCIA: Esto se pierde si el bot se reinicia. Necesitas una solución persistente.
pagos_confirmados = set() # Almacena user_ids que han pagado

# Variable global para la aplicación de Telegram (para acceder a app.bot desde handlers de aiohttp)
telegram_app: Application = None

# --- FUNCIONES DE PAYPAL ---
async def obtener_token_paypal():
    """Obtiene un token de acceso OAuth2 de PayPal."""
    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        data = {'grant_type': 'client_credentials'}
        try:
            async with session.post(f"{PAYPAL_API_BASE_URL}/v1/oauth2/token", auth=auth, data=data) as resp:
                resp.raise_for_status() # Lanza excepción para errores HTTP
                token_data = await resp.json()
                return token_data.get("access_token")
        except aiohttp.ClientError as e:
            print(f"[ERROR PayPal Token] No se pudo obtener token: {e}")
            return None

async def crear_orden_paypal(user_id: int, item_description: str, amount: str):
    """Crea una orden de pago en PayPal y devuelve el enlace de aprobación."""
    access_token = await obtener_token_paypal()
    if not access_token:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        # "PayPal-Request-Id": f"order-{user_id}-{int(time.time())}" # Para idempotencia, opcional
    }
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "description": item_description,
            "amount": {
                "currency_code": "USD",
                "value": amount
            },
            "custom_id": str(user_id)  # Importante para rastrear quién pagó
        }],
        "application_context": {
            "brand_name": "Bot MLBB Tutoriales",
            "landing_page": "LOGIN", # O GUEST_CHECKOUT
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW",
            "return_url": f"{WEBHOOK_URL}/payment/success?user_id={user_id}", # URL a la que el usuario es redirigido
            "cancel_url": f"{WEBHOOK_URL}/payment/cancel?user_id={user_id}"  # URL si el usuario cancela
        }
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{PAYPAL_API_BASE_URL}/v2/checkout/orders", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                order_data = await resp.json()
                # print(f"[PayPal Order Created] Data: {order_data}")
                for link in order_data.get("links", []):
                    if link.get("rel") == "approve":
                        return link["href"] # Este es el enlace que el usuario debe visitar
                print("[ERROR PayPal Order] No se encontró el enlace 'approve'.")
                return None
        except aiohttp.ClientError as e:
            error_details = "Desconocido"
            try:
                error_details = await resp.json()
            except:
                pass
            print(f"[ERROR PayPal Order] No se pudo crear la orden: {e}. Detalles: {error_details}")
            return None

async def capturar_pago_paypal(order_id: str):
    """Captura un pago para una orden de PayPal aprobada."""
    access_token = await obtener_token_paypal()
    if not access_token:
        return False, "Error obteniendo token de PayPal para captura."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    # El payload vacío es correcto para capturar la orden entera
    payload = {}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}/capture", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                capture_data = await resp.json()
                # print(f"[PayPal Capture] Data: {capture_data}")
                if capture_data.get("status") == "COMPLETED":
                    return True, capture_data
                else:
                    return False, f"Captura no completada: {capture_data.get('status')}"
        except aiohttp.ClientError as e:
            error_details = "Desconocido"
            try:
                error_details = await resp.json()
            except:
                pass
            print(f"[ERROR PayPal Capture] No se pudo capturar el pago {order_id}: {e}. Detalles: {error_details}")
            return False, f"Error al capturar pago: {e}"

# --- HANDLERS DE TELEGRAM ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Bienvenido al bot. Usa /menu para ver las opciones.")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Video Tutorial ($1 USD)", callback_data="video_tutorial")],
        [InlineKeyboardButton("ℹ Información de Texturas", callback_data="info_texturas")],
        [InlineKeyboardButton("🛠 Activar Desarrollador", callback_data="activar_desarrollador")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Por favor, elige una opción del menú:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Es importante responder al callback query
    user_id = query.from_user.id

    if query.data == "video_tutorial":
        if user_id in pagos_confirmados:
            mensaje_contenido = (
                "¡Gracias por tu compra! Aquí tienes acceso al contenido:\n\n"
                f"🎬 Video tutorial (Drive):\n{VIDEO_TUTORIAL_DRIVE_LINK}\n\n"
                f"📺 Solución (YouTube):\n{VIDEO_TUTORIAL_YOUTUBE_LINK}"
            )
            await query.edit_message_text(text=mensaje_contenido)
        else:
            await query.edit_message_text(text="⌛ Procesando tu solicitud de pago...")
            payment_link = await crear_orden_paypal(
                user_id=user_id,
                item_description="Acceso Video Tutorial MLBB",
                amount=PRECIO_VIDEO_TUTORIAL
            )
            if payment_link:
                keyboard_pago = [[InlineKeyboardButton("🔗 Pagar $1.00 USD con PayPal", url=payment_link)]]
                reply_markup_pago = InlineKeyboardMarkup(keyboard_pago)
                await query.edit_message_text(
                    text="Haz clic en el botón de abajo para completar tu pago de $1.00 USD por el video tutorial.",
                    reply_markup=reply_markup_pago
                )
            else:
                await query.edit_message_text(text="❌ Lo sentimos, hubo un error al generar el enlace de pago. Por favor, inténtalo más tarde.")

    elif query.data == "info_texturas":
        msg = (
            "Las texturas (mods visuales) que se proporcionan cambian únicamente la apariencia estética "
            "de los héroes o elementos dentro del juego. No alteran las mecánicas de juego, "
            "habilidades, estadísticas ni ofrecen ventajas competitivas. Por esta razón, su uso es "
            "generalmente considerado seguro y no suele ser motivo de penalización por parte de los desarrolladores del juego."
        )
        await query.edit_message_text(text=msg)

    elif query.data == "activar_desarrollador":
        mensaje = (
            "<b>Modo desarrollador - Enlaces de interés:</b>\n"
            "🔍 TikTok 1: https://vm.tiktok.com/ZMSJnGE8F/\n"
            "🔍 TikTok 2: https://vm.tiktok.com/ZMSJncaNf/\n"
            "🔍 TikTok 3: https://vm.tiktok.com/ZMSJn3F2z/\n"
            "🔍 TikTok 4: https://vm.tiktok.com/ZMSJn7EC6/\n"
            "🔍 TikTok 5: https://vm.tiktok.com/ZMSJWRPjP/\n"
            "🔍 TikTok 6: https://vm.tiktok.com/ZMSJWfUNA/"
        )
        await query.edit_message_text(text=mensaje, parse_mode=ParseMode.HTML)

# --- HANDLERS DE AIOHTTP (WEBHOOKS) ---
async def telegram_webhook_handler(request: web.Request):
    """Maneja las actualizaciones entrantes de Telegram."""
    bot_app = request.app['bot_app'] # Acceder a la app de telegram
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return web.Response(status=200)
    except json.JSONDecodeError:
        print("[ERROR Telegram Webhook] Payload no es JSON válido.")
        return web.Response(text="Invalid JSON", status=400)
    except Exception as e:
        print(f"[ERROR Telegram Webhook] Error procesando update: {e}")
        return web.Response(status=500)

async def paypal_webhook_handler(request: web.Request):
    """
    Maneja los webhooks de PayPal.
    PayPal enviará notificaciones aquí (ej: CHECKOUT.ORDER.APPROVED).
    Este endpoint DEBE estar configurado en tu aplicación de PayPal Developer.
    """
    bot = request.app['bot_app'].bot # Acceder al bot de telegram
    try:
        payload = await request.json()
        # print(f"[PayPal Webhook Received] Event: {payload.get('event_type')}, Resource: {payload.get('resource')}")

        # --- IMPORTANTE: Verificar la firma del webhook de PayPal en producción ---
        # Esto requiere configurar el ID del Webhook en PayPal y usar el SDK o lógica de verificación.
        # Por ahora, omitimos esta verificación para simplificar.

        event_type = payload.get("event_type")
        resource = payload.get("resource", {})

        if event_type == "CHECKOUT.ORDER.APPROVED":
            order_id = resource.get("id")
            if not order_id:
                print("[PayPal Webhook] CHECKOUT.ORDER.APPROVED sin order_id.")
                return web.Response(status=400, text="Missing order_id")

            # Extraer el custom_id (user_id de Telegram)
            # La estructura puede variar un poco, asegúrate de que custom_id esté donde esperas
            user_id_str = None
            if resource.get("purchase_units") and len(resource["purchase_units"]) > 0:
                user_id_str = resource["purchase_units"][0].get("custom_id")

            if not user_id_str:
                print(f"[PayPal Webhook] No se encontró custom_id para la orden {order_id}.")
                # Podrías intentar buscar el user_id en tu base de datos si almacenas order_id temporalmente
                return web.Response(status=400, text="Missing custom_id")

            try:
                user_id = int(user_id_str)
            except ValueError:
                print(f"[PayPal Webhook] custom_id '{user_id_str}' no es un entero válido para la orden {order_id}.")
                return web.Response(status=400, text="Invalid custom_id format")

            print(f"[PayPal Webhook] Orden {order_id} aprobada por usuario {user_id}.")

            # Capturar el pago
            # Es crucial capturar el pago después de que es aprobado.
            success, result = await capturar_pago_paypal(order_id)
            if success:
                print(f"[✔ PAGO CAPTURADO] Orden {order_id} para usuario {user_id}.")
                pagos_confirmados.add(user_id) # Marcar como pagado

                # **ENVIAR CONTENIDO AL USUARIO**
                mensaje_contenido = (
                    "¡Tu pago de $1.00 USD ha sido confirmado! 🎉\n\n"
                    "Aquí tienes acceso al contenido:\n"
                    f"🎬 Video tutorial (Drive):\n{VIDEO_TUTORIAL_DRIVE_LINK}\n\n"
                    f"📺 Solución (YouTube):\n{VIDEO_TUTORIAL_YOUTUBE_LINK}\n\n"
                    "Gracias por tu compra."
                )
                try:
                    await bot.send_message(chat_id=user_id, text=mensaje_contenido)
                    print(f"[✔ Contenido Enviado] A usuario {user_id} por orden {order_id}.")
                except Exception as e:
                    print(f"[ERROR Telegram Send] No se pudo enviar mensaje a {user_id} tras pago: {e}")
                    # Aquí deberías tener un sistema para reintentar o notificar al admin.
            else:
                print(f"[❌ FALLO CAPTURA] Orden {order_id} para usuario {user_id}. Razón: {result}")
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"Hubo un problema al procesar tu pago (Orden {order_id}). Por favor, contacta a soporte."
                    )
                except Exception as e:
                    print(f"[ERROR Telegram Send] No se pudo notificar error de captura a {user_id}: {e}")
        
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            # Este evento también puede ser útil para confirmar que el dinero se movió.
            # El custom_id estaría en resource.custom_id o resource.purchase_units[0].payments.captures[0].custom_id
            print(f"[PayPal Webhook] Captura completada: {resource.get('id')}")
            # Podrías tener lógica adicional aquí si es necesario.

        # Otros eventos de PayPal pueden ser manejados aquí (ej. reembolsos, disputas)

        return web.Response(status=200, text="Webhook received") # Siempre responde 200 a PayPal si procesas el evento

    except json.JSONDecodeError:
        print("[ERROR PayPal Webhook] Payload no es JSON válido.")
        return web.Response(text="Invalid JSON", status=400)
    except Exception as e:
        print(f"[ERROR PayPal Webhook] Error inesperado: {e}")
        # Enviar stack trace para depuración si es necesario
        import traceback
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error")

# Rutas para redirección de PayPal (return_url, cancel_url)
async def paypal_payment_success_handler(request: web.Request):
    user_id = request.query.get("user_id")
    # token = request.query.get("token") # Order ID (PayerID es otro parámetro)
    # PayerID = request.query.get("PayerID")
    # Aquí podrías enviar un mensaje al bot, o simplemente mostrar una página de éxito.
    # El webhook es el mecanismo primario para confirmar el pago.
    # Esta página es solo para la UX del usuario.
    text_response = (
        "<html><head><title>Pago en Proceso</title></head>"
        "<body><h1>¡Gracias! Estamos procesando tu pago.</h1>"
        "<p>Recibirás una notificación en Telegram en breve una vez que se confirme.</p>"
        "<p>Si no recibes nada en unos minutos, por favor, revisa el bot o contacta a soporte.</p>"
        f"<p>(Usuario: {user_id})</p>"
        "</body></html>"
    )
    return web.Response(text=text_response, content_type='text/html', status=200)

async def paypal_payment_cancel_handler(request: web.Request):
    user_id = request.query.get("user_id")
    # token = request.query.get("token") # Order ID
    text_response = (
        "<html><head><title>Pago Cancelado</title></head>"
        "<body><h1>Pago Cancelado</h1>"
        "<p>Tu pago ha sido cancelado. Puedes cerrar esta ventana y volver a intentarlo desde el bot si lo deseas.</p>"
        f"<p>(Usuario: {user_id})</p>"
        "</body></html>"
    )
    return web.Response(text=text_response, content_type='text/html', status=200)


# --- FUNCIÓN PRINCIPAL Y ARRANQUE ---
async def main():
    global telegram_app # Hacemos la app de telegram global para accederla desde aiohttp

    # Configurar la aplicación de Telegram
    telegram_app = ApplicationBuilder().token(TOKEN).build()

    # Añadir handlers de Telegram
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("menu", menu_command))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))

    # Inicializar la aplicación de Telegram (necesario para set_webhook)
    await telegram_app.initialize()

    # Configurar el webhook de Telegram
    # Render usualmente expone la app en `https://<nombre-app>.onrender.com`
    # El path `/telegram` es donde nuestro servidor aiohttp escuchará.
    telegram_webhook_path = "/telegram_webhook" # Un path único para el webhook de Telegram
    full_telegram_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{telegram_webhook_path}"

    await telegram_app.bot.set_webhook(
        url=full_telegram_webhook_url,
        allowed_updates=Update.ALL_TYPES # O especifica los tipos que necesitas
    )
    print(f"[INFO] Webhook de Telegram configurado en: {full_telegram_webhook_url}")
    webhook_info = await telegram_app.bot.get_webhook_info()
    print(f"[INFO] Información del Webhook de Telegram: {webhook_info}")


    # Configurar el servidor web aiohttp
    aiohttp_app = web.Application()
    aiohttp_app['bot_app'] = telegram_app # Pasar la app de telegram a los handlers de aiohttp

    # Ruta para el webhook de Telegram
    aiohttp_app.router.add_post(telegram_webhook_path, telegram_webhook_handler)
    
    # Ruta para el webhook de PayPal (esta URL la configuras en PayPal Developer Dashboard)
    paypal_webhook_path = "/paypal_webhook_listener" # Un path único
    print(f"[INFO] Endpoint para Webhook de PayPal (configurar en PayPal): {WEBHOOK_URL.rstrip('/')}{paypal_webhook_path}")
    aiohttp_app.router.add_post(paypal_webhook_path, paypal_webhook_handler)

    # Rutas para return_url y cancel_url de PayPal
    aiohttp_app.router.add_get("/payment/success", paypal_payment_success_handler)
    aiohttp_app.router.add_get("/payment/cancel", paypal_payment_cancel_handler)

    # Iniciar el servidor aiohttp
    port = int(os.environ.get("PORT", 8080)) # Render establece la variable PORT
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port) # Escuchar en 0.0.0.0 para Render
    await site.start()

    print(f"[INFO] Bot iniciado y servidor web escuchando en el puerto {port}")
    print(f"[INFO] URL base de la app (Render): {WEBHOOK_URL}")
    print(f"[INFO] Visita {WEBHOOK_URL}{telegram_webhook_path} para ver si el webhook de Telegram responde (debería dar error si no es POST de Telegram).")
    print(f"[INFO] Visita {WEBHOOK_URL}{paypal_webhook_path} para ver si el webhook de PayPal responde (debería dar error si no es POST de PayPal).")


    # Mantener la aplicación corriendo (aiohttp lo hace implícitamente con await site.start())
    # El bucle while True ya no es estrictamente necesario si solo usas webhooks.
    # Pero si tienes tareas en segundo plano con asyncio.create_task, esto las mantendría vivas.
    # Por ahora, lo dejamos simple.
    await asyncio.Event().wait() # Mantiene la corutina principal viva indefinidamente

if __name__ == "__main__":
    # Asegúrate de que las variables de entorno cruciales estén configuradas
    if not all([TOKEN, PAYPAL_CLIENT_ID, PAYPAL_SECRET, WEBHOOK_URL]) or \
       "TU_" in TOKEN or "TU_" in PAYPAL_CLIENT_ID or "TU_" in PAYPAL_SECRET or "TU_" in WEBHOOK_URL:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR DE CONFIGURACIÓN:                               !!!")
        print("!!! Por favor, configura las variables de entorno:        !!!")
        print("!!! TELEGRAM_BOT_TOKEN, PAYPAL_CLIENT_ID, PAYPAL_SECRET,  !!!")
        print("!!! y RENDER_EXTERNAL_URL (o WEBHOOK_URL directamente).   !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # exit(1) # Comentado para que puedas probar localmente sin variables si quieres, pero fallará con PayPal/Telegram.
    
    # Para Paypal Sandbox vs Producción
    # PAYPAL_API_BASE_URL = "https://api-m.paypal.com" # Para producción
    # PAYPAL_API_BASE_URL = "https://api-m.sandbox.paypal.com" # Para sandbox (pruebas)
    # Asegúrate de que PAYPAL_CLIENT_ID y PAYPAL_SECRET correspondan al entorno.
    print(f"[INFO] Usando API de PayPal: {PAYPAL_API_BASE_URL}")


    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Cerrando bot...")
    finally:
        # Aquí podrías añadir lógica de limpieza si es necesario
        if telegram_app: # Si la app se inicializó
            # Considera eliminar el webhook al apagar para evitar errores si la URL cambia.
            # asyncio.run(telegram_app.bot.delete_webhook())
            # print("Webhook de Telegram eliminado.")
            pass
        print("Bot detenido.")