from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import os

from .payments import generar_enlace_de_pago, verificar_pago

# /start
async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenido, presiona /menu para ver las opciones disponibles.")

# /menu
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📽 Video Tutorial", callback_data="video_tutorial")],
        [InlineKeyboardButton("ℹ Información de Texturas", callback_data="info_texturas")],
        [InlineKeyboardButton("🛠 Activar Modo Desarrollador", callback_data="activar_desarrollador")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = "<b>Menú de Comandos Disponibles:</b>\n\nSelecciona una opción:"
    await update.message.reply_text(mensaje, parse_mode="HTML", reply_markup=reply_markup)

# Manejar botones
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "video_tutorial":
        user_id = str(query.from_user.id)
        pago_realizado = verificar_pago(user_id)

        if pago_realizado:
            enlace = "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk"
            await query.edit_message_text(f"Aquí tienes el video tutorial sobre texturas:\n{enlace}")
        else:
            link_pago = generar_enlace_de_pago(user_id)
            await query.edit_message_text(
                text=f"💵 Para ver el video tutorial, debes pagar 1 USD:\n{link_pago}\n\nLuego de pagar, presiona nuevamente el botón."
            )

    elif query.data == "info_texturas":
        mensaje = (
            "Las texturas, mejor conocidas como mods, existen en muchos juegos como Free Fire, Dota 2 y muchos más..."
        )
        await query.edit_message_text(text=mensaje)
        video_path = "info_texturas.mp4"
        if os.path.exists(video_path):
            with open(video_path, "rb") as video_file:
                await query.message.reply_video(video=video_file, caption="Video Ejemplo de las Texturas.")
        else:
            await query.message.reply_text("El archivo 'info_texturas.mp4' no fue encontrado.")

    elif query.data == "activar_desarrollador":
        links = [
            "https://www.tiktok.com/@usuario1/video/123456789",
            "https://www.tiktok.com/@usuario2/video/987654321",
            "https://www.tiktok.com/@usuario3/video/567891234"
        ]
        await query.edit_message_text("🎥 Videos de desarrollo activados para diferentes marcas:\n" + "\n".join(links))

# Comandos directos (opcionales)
async def send_video_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enlace = "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk"
    await update.message.reply_text(f"Aquí tienes el video tutorial:\n{enlace}")

async def send_info_texturas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "Las texturas, mejor conocidas como mods, existen en muchos juegos como Free Fire, Dota 2 y muchos más. Estos mods no son baneables, ya que no alteran el juego; solo cambian la apariencia básica (por defecto) del héroe, y solo tú puedes ver los cambios. De esta manera, este mod no afecta el rendimiento de otros jugadores."
    )
    await update.message.reply_text(mensaje)
    video_path = "info_texturas.mp4"
    if os.path.exists(video_path):
        with open(video_path, "rb") as video_file:
            await update.message.reply_video(video=video_file, caption="Video Ejemplo de las Texturas.")
    else:
        await update.message.reply_text("El archivo 'info_texturas.mp4' no fue encontrado.")
