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
        # Paso 1: Verificar si ya tenemos un order_id en memoria
        if "order_id" in context.user_data:
            order_id = context.user_data["order_id"]
            if verificar_pago(order_id):
                enlace_drive = "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk"
                enlace_youtube = "https://youtu.be/8ZEExAeS4aQ?si=lfG7BvAhr1HOGzZ0"
                mensaje = f"Aquí tienes el video tutorial sobre texturas:\n{enlace_drive}\n\nTambién te dejo un video complementario en YouTube:\n{enlace_youtube}"
                await query.edit_message_text(mensaje)
                return
            else:
                await query.message.reply_text("Tu pago aún no ha sido confirmado. Si ya pagaste, espera unos segundos y vuelve a presionar el botón.")
                return

        # Paso 2: Generar el enlace de pago
        enlace_pago = generar_enlace_de_pago(query.from_user.id)
        if "paypal.com" in enlace_pago:
            try:
                order_id = enlace_pago.split("/")[5]
                context.user_data["order_id"] = order_id
                await query.message.reply_text(
                    f"💵 Para ver el video tutorial, realiza el pago de 1 USD:\n{enlace_pago}\n\nLuego vuelve a presionar este botón."
                )
            except Exception as e:
                await query.message.reply_text("No se pudo generar el pago correctamente. Inténtalo más tarde.")
                print(f"Error al generar el enlace de pago: {e}")
        else:
            await query.message.reply_text("Ocurrió un error al generar el enlace de pago.")

    elif query.data == "info_texturas":
        mensaje = (
            "Las texturas, mejor conocidas como mods, existen en muchos juegos como Free Fire, Dota 2 y muchos más..."
        )
        await query.edit_message_text(text=mensaje)

        # Verificación del archivo info_texturas.mp4
        video_path = "info_texturas.mp4"
        if os.path.exists(video_path):
            with open(video_path, "rb") as video_file:
                await query.message.reply_video(video=video_file, caption="Video Ejemplo de las Texturas.")
        else:
            await query.message.reply_text("El archivo 'info_texturas.mp4' no fue encontrado en el directorio.")

    elif query.data == "activar_desarrollador":
        links = [
            "https://vm.tiktok.com/ZMSJnGE8F/",
            "https://vm.tiktok.com/ZMSJncaNf/",
            "https://vm.tiktok.com/ZMSJno3YP/",
            "https://vm.tiktok.com/ZMSJn7EC6/",
            "https://vm.tiktok.com/ZMSJWRPjP/",
            "https://vm.tiktok.com/ZMSJWfUNA/"
        ]
        await query.edit_message_text("🎥 Videos de desarrollo activados para diferentes marcas:\n" + "\n".join(links))

# Comandos directos (opcionales)
async def send_video_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enlace_drive = "https://drive.google.com/file/d/1G_Idowx9lPCYd5vgKFv3L_6kcbkW_Rte/view?usp=drivesdk"
    enlace_youtube = "https://youtu.be/8ZEExAeS4aQ?si=lfG7BvAhr1HOGzZ0"
    mensaje = f"Aquí tienes el video tutorial:\n{enlace_drive}\n\nTambién te dejo un video complementario en YouTube:\n{enlace_youtube}"
    await update.message.reply_text(mensaje)

async def send_info_texturas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "Las texturas, mejor conocidas como mods, existen en muchos juegos como Free Fire, Dota 2 y muchos más. "
        "Estos mods no son baneables, ya que no alteran el juego; solo cambian la apariencia básica del héroe. "
        "Solo tú puedes ver los cambios, por lo tanto no afecta a otros jugadores."
    )
    await update.message.reply_text(mensaje)

    # Verificación del archivo info_texturas.mp4
    video_path = "info_texturas.mp4"
    if os.path.exists(video_path):
        with open(video_path, "rb") as video_file:
            await update.message.reply_video(video=video_file, caption="Video Ejemplo de las Texturas.")
    else:
        await update.message.reply_text("El archivo 'info_texturas.mp4' no fue encontrado en el directorio.")

