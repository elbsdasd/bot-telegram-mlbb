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
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# --- ENLACES PARA EL VIDEO TUTORIAL ---
# ¡¡ASEGÚRATE DE ACTUALIZAR ESTAS URLS!!
LINK_VIDEO_TUTORIAL_PRINCIPAL = "https://cuty.io/wK25kGsx331U" # Reemplaza con tu URL
LINK_VIDEO_TUTORIAL_COMPLEMENTO = "https://cuty.io/KniC"    # Reemplaza con tu URL

telegram_app: Application = None

# --- HANDLERS DE TELEGRAM ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    keyboard = [
        [InlineKeyboardButton("➡️ Ver Menú ⬅️", callback_data="mostrar_menu_principal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"¡Hola {user_name}! 👋\nBienvenido al bot de tutoriales.\nPresiona el botón de abajo para ver las opciones disponibles.",
        reply_markup=reply_markup
    )

async def mostrar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Video Tutorial (Gratis)", callback_data="video_tutorial")],
        [InlineKeyboardButton("ℹ Información de Texturas", callback_data="info_texturas")],
        [InlineKeyboardButton("🛠 Activar Desarrollador", callback_data="activar_desarrollador")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Por favor, elige una opción del menú:", reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text("Por favor, elige una opción del menú:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "mostrar_menu_principal":
        await mostrar_menu_principal(update, context)

    elif query.data == "video_tutorial":
        keyboard_video = [
            [InlineKeyboardButton("🔗 Link del video tutorial", url=LINK_VIDEO_TUTORIAL_PRINCIPAL)],
            [InlineKeyboardButton("🔗 Complemento del video tutorial", url=LINK_VIDEO_TUTORIAL_COMPLEMENTO)],
            [InlineKeyboardButton("⬅️ Volver al Menú", callback_data="mostrar_menu_principal")]
        ]
        reply_markup_video = InlineKeyboardMarkup(keyboard_video)
        await query.edit_message_text(
            text="Aquí tienes los enlaces para el video tutorial y su complemento:",
            reply_markup=reply_markup_video,
            disable_web_page_preview=True
        )

    elif query.data == "info_texturas":
        msg_caption = (
            "Las texturas (mods visuales) existen en la mayoria de vidiojuegos ya sea Dota 2, free fire y muchos más, estas cambian únicamente la apariencia estética "
            "de los héroes o elementos dentro del juego. No alteran las mecánicas de juego, "
            "habilidades, estadísticas ni ofrecen ventajas competitivas. Por esta razón, su uso es "
            "generalmente considerado seguro y no suele ser motivo de penalización por parte de los desarrolladores del juego."
        )
        video_filename = "inf_texturas.mp4"

        try:
            await query.delete_message()
        except Exception as e:
            print(f"Advertencia: No se pudo borrar el mensaje anterior (info_texturas): {e}")

        try:
            with open(video_filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=msg_caption
                )
            print(f"Video '{video_filename}' enviado a {chat_id} para info_texturas.")
            
            keyboard_back = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="mostrar_menu_principal")]]
            reply_markup_back = InlineKeyboardMarkup(keyboard_back)
            await context.bot.send_message(chat_id=chat_id, text="¿Deseas ver otras opciones?", reply_markup=reply_markup_back)

        except FileNotFoundError:
            print(f"[ERROR] Archivo de video no encontrado: {video_filename}")
            keyboard_back = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="mostrar_menu_principal")]]
            reply_markup_back = InlineKeyboardMarkup(keyboard_back)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{msg_caption}\n\n(Video no disponible en este momento)",
                reply_markup=reply_markup_back
            )
        except Exception as e:
            print(f"[ERROR] Ocurrió un error al enviar el video '{video_filename}': {e}")
            keyboard_back = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="mostrar_menu_principal")]]
            reply_markup_back = InlineKeyboardMarkup(keyboard_back)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{msg_caption}\n\n(Error al cargar el video)",
                reply_markup=reply_markup_back
            )

    elif query.data == "activar_desarrollador":
        mensaje = (
            "<b>Modo desarrollador - Enlaces de interés:</b>\n"
            "🔍 TikTok 1: https://vm.tiktok.com/ZMSJnGE8F/\n"
            "🔍 TikTok 2: https://vm.tiktok.com/ZMSJncaNf/\n"
            "🔍 TikTok 3: https://vm.tiktok.com/ZMSJn3F2z/\n"
            "🔍 TikTok 4: https://vm.tiktok.com/ZMSJn7EC6/\n"
            "🔍 TikTok 5: https://vm.tiktok.com/ZMSJWRPjP/\n"
            "🔍 TikTok 6: https://vm.tiktok.com/ZMSJWfUNA/\n\n"
            "<i>Presiona abajo para regresar.</i>"
        )
        keyboard_back = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="mostrar_menu_principal")]]
        reply_markup_back = InlineKeyboardMarkup(keyboard_back)
        await query.edit_message_text(text=mensaje, parse_mode=ParseMode.HTML, reply_markup=reply_markup_back)

# --- HANDLER DE AIOHTTP (WEBHOOK DE TELEGRAM) ---
async def telegram_webhook_handler(request: web.Request):
    bot_app = request.app['bot_app']
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
        return web.Response(status=200)

# --- FUNCIÓN PRINCIPAL Y ARRANQUE ---
async def main():
    global telegram_app

    if not TOKEN or not WEBHOOK_URL:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR DE CONFIGURACIÓN:                               !!!")
        print("!!! Por favor, configura TELEGRAM_BOT_TOKEN y             !!!")
        print("!!! RENDER_EXTERNAL_URL en tus variables de entorno.      !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    telegram_app = ApplicationBuilder().token(TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))

    await telegram_app.initialize()

    telegram_webhook_path = "/telegram_webhook"
    full_telegram_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{telegram_webhook_path}"

    try:
        current_webhook_info = await telegram_app.bot.get_webhook_info()
        if current_webhook_info and current_webhook_info.url == full_telegram_webhook_url:
            print(f"[INFO] Webhook de Telegram ya está configurado correctamente en: {full_telegram_webhook_url}")
        else:
            if current_webhook_info and current_webhook_info.url:
                print(f"[INFO] Eliminando webhook anterior: {current_webhook_info.url}")
                await telegram_app.bot.delete_webhook(drop_pending_updates=True)
            
            await telegram_app.bot.set_webhook(
                url=full_telegram_webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            print(f"[INFO] Webhook de Telegram configurado en: {full_telegram_webhook_url}")
        
        webhook_info = await telegram_app.bot.get_webhook_info()
        print(f"[INFO] Información del Webhook de Telegram actual: {webhook_info}")

    except Exception as e:
        print(f"[ERROR CRÍTICO] No se pudo configurar el webhook de Telegram: {e}")
        print("Por favor, verifica tu TELEGRAM_BOT_TOKEN y RENDER_EXTERNAL_URL.")
        print("Asegúrate de que RENDER_EXTERNAL_URL sea la URL pública correcta de tu servicio en Render (HTTPS).")
        return

    aiohttp_app = web.Application()
    aiohttp_app['bot_app'] = telegram_app
    aiohttp_app.router.add_post(telegram_webhook_path, telegram_webhook_handler)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()

    print(f"[INFO] Bot iniciado y servidor web escuchando en http://0.0.0.0:{port}")
    print(f"[INFO] URL base de la app (Render): {WEBHOOK_URL}")
    
    await asyncio.Event().wait()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Cerrando bot por KeyboardInterrupt...")
    except Exception as e_global:
        print(f"Error global inesperado durante la ejecución de main(): {e_global}")
    finally:
        print("Ejecutando limpieza final...")
        if telegram_app:
            try:
                webhook_info_at_shutdown = loop.run_until_complete(telegram_app.bot.get_webhook_info())
                if webhook_info_at_shutdown and webhook_info_at_shutdown.url:
                    print(f"[INFO] Intentando eliminar webhook: {webhook_info_at_shutdown.url}")
                    loop.run_until_complete(telegram_app.bot.delete_webhook(drop_pending_updates=True))
                    print("[INFO] Webhook de Telegram eliminado en el cierre final.")
                else:
                    print("[INFO] No había webhook configurado para eliminar o no se pudo obtener información.")
            except Exception as e_del_webhook:
                print(f"[ERROR] No se pudo eliminar el webhook en el cierre final: {e_del_webhook}")
        
        try:
            all_tasks = asyncio.all_tasks(loop=loop)
            for task in all_tasks:
                if not task.done(): # Solo cancelar tareas que no hayan terminado
                    task.cancel()
            # Dar tiempo a las tareas para que se cancelen
            loop.run_until_complete(asyncio.gather(*[task for task in all_tasks if not task.done()], return_exceptions=True))
        except RuntimeError as e_runtime: # Puede ocurrir si el loop ya está cerrado
            print(f"Error durante la cancelación de tareas (puede ser normal si el loop ya estaba cerrado): {e_runtime}")
        except Exception as e_cancel:
            print(f"Error inesperado durante la cancelación de tareas: {e_cancel}")
        finally:
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
            print("Loop de asyncio cerrado. Bot detenido.")