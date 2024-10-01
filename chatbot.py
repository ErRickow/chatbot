import asyncio
import os
import sys
import time
import subprocess
from collections import defaultdict
from dotenv import load_dotenv
from mytools import Api, BinaryEncryptor, Button, Extract, Handler, ImageGen, LoggerHandler, Translate
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.errors import FloodWait

load_dotenv(sys.argv[1])

logger = LoggerHandler()
logger.setup_logger()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
DEV_NAME = os.getenv("DEV_NAME")

app = Client(name=BOT_TOKEN.split(":")[0], api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# All users can interact with the chatbot
chatbot_active = True  # Initialize chatbot status as active
user_last_response_time = defaultdict(lambda: 0)  # Dictionary to track user response times
response_cooldown = 3  # Cooldown duration in seconds
my_api = Api(name=BOT_NAME, dev=DEV_NAME)
trans = Translate()
binary = BinaryEncryptor(1945)

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    keyboard = [
        {"text": "Developer", "url": "https://t.me/chakszzz"},
        {"text": "Channel", "url": "https://t.me/ZeebSupport"},
        {"text": "Ubot?", "url": "https://t.me/erprembot"},
    ]
    reply_markup = Button().generateInlineButtonGrid(keyboard)

    await message.reply_text(
        f"**👋 Hai {Extract().getMention(message.from_user)}!**\n",
        "Kenalin nih, gue bot pintar berbasis Python dari mytoolsID. Gue siap bantu jawab semua pertanyaan lo.\n\n",
        "Lu bisa make bot-nya di grup lo ya. Masih project Balu.",
        reply_markup=reply_markup,
    )
    logger.get_logger(__name__).info("Mengirim pesan selamat datang")

@app.on_message(filters.command(["bencode", "bdecode"]))
async def handle_encrypt(client, message):
    cmd = message.command[0]
    msg = await message.reply("**Tunggu bentar ya...**")

    text = Handler().getArg(message)
    if not text:
        return await msg.edit(f"{message.text.split()[0]} balas ke text atau ketik sesuatu")

    code = binary.encrypt(text) if cmd == "bencode" else binary.decrypt(text)
    await msg.delete()
    return await Handler().sendLongPres(message, code)

@app.on_message(filters.command("clear"))
async def handle_clear_message(client, message):
    clear = my_api.clear_chat_history(message.from_user.id)
    await message.reply(clear)

# Di bagian atas kode, tambahkan variabel untuk menyimpan ID pemilik bot
OWNER_ID = 1448273246  # Ganti dengan ID pemilik bot Anda

@app.on_message(filters.text & ~filters.bot & ~filters.me & filters.group)
async def handle_message(client, message):
    global chatbot_active  # Ensure we can modify the global variable

    # Check if the message text is "on" or "off" to set the chatbot's active status
    text = message.text.lower()
    if "on" in text:
        chatbot_active = True
        await message.reply("Chatbot sekarang **aktif**.")
        logger.get_logger(__name__).info("Chatbot diaktifkan.")
        return
    elif "off" in text:
        chatbot_active = False
        await message.reply("Chatbot sekarang **non-aktif**.")
        logger.get_logger(__name__).info("Chatbot dinonaktifkan.")
        return

    # Ganti bagian ini
    if "update" in text:
        # Cek apakah pengguna adalah pemilik bot
        if message.from_user.id != OWNER_ID:
            await message.reply("Anda tidak memiliki izin untuk melakukan pembaruan.")
            return

        logger.get_logger(__name__).info("Memulai proses update bot.")
        try:
            pros = await message.reply(
                f"<i>Memeriksa pembaruan untuk {app.me.mention}...</i>"
            )
            out = subprocess.check_output(["git", "pull"]).decode("UTF-8")

            if "Already up to date." in str(out):
                return await pros.edit(
                    f"<blockquote>✅ Pembaruan berhasil! Bot sudah terbaru.</blockquote>"
                )

            # Menghapus informasi commit
            await pros.edit(
                f"<blockquote>🔄 Pembaruan berhasil! Bot telah diperbarui.</blockquote>"
            )

            os.execl(sys.executable, sys.executable, "-m", "Ah")

        except Exception as e:
            await message.reply(f"Terjadi kesalahan saat memperbarui: {e}")
            logger.error(f"Error saat memperbarui bot: {e}")

        return

    # Cooldown mechanism
    current_time = time.time()
    last_response_time = user_last_response_time[message.from_user.id]

    # Check if the cooldown has expired
    if current_time - last_response_time < response_cooldown:
        return  # Do not respond if within cooldown period

    # Update last response time
    user_last_response_time[message.from_user.id] = current_time

    # Check if chatbot is active before processing
    if not chatbot_active:  
        return

    logger.get_logger(__name__).info(f"Menerima pesan dari pengguna dengan ID: {message.from_user.id}")

    await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        result = my_api.ChatBot(message)
        logger.get_logger(__name__).info("Mengirim output besar ke pengguna")
        await Handler().sendLongPres(message, result)
    except FloodWait as e:
        await asyncio.sleep(e.x)  # Wait for the required time before retrying
    except Exception as e:
        await Handler().sendLongPres(message, f"Terjadi kesalahan: {str(e)}")
        logger.get_logger(__name__).error(f"Terjadi kesalahan: {str(e)}")

@app.on_message(filters.command(["tts", "tr"]))
async def handle_tts(client, message):
    msg = await message.reply("**Tunggu bentar ya...**")
    text = Handler().getArg(message)

    if not text:
        return await msg.edit(f"{message.text.split()[0]} (replyText/typingText)")

    command = message.command[0].upper()
    logger.get_logger(__name__).info(f"Menerima permintaan {command} dari user ID {message.from_user.id}")

    try:
        if command == "TTS":
            result = trans.TextToSpeech(text)
            await message.reply_voice(result)
            os.remove(result)
        else:
            result = trans.ConvertLang(text)
            await Handler().sendLongPres(message, result)

        logger.get_logger(__name__).info(f"Berhasil mengirimkan {command} ke user ID {message.from_user.id}")
        await msg.delete()
    except FloodWait as e:
        await asyncio.sleep(e.x)  # Wait for the required time before retrying
    except Exception as e:
        logger.get_logger(__name__).error(f"Error generating {command}: {e}")
        await msg.edit(f"Error: {str(e)}")

@app.on_message(filters.command("khodam"))
async def handle_khodam(client, message):
    msg = await message.reply("**Sedang memproses....**")

    try:
        user = await Extract().getId(message)
        if not user:
            return await msg.edit("**harap berikan username atau reply ke pengguna untuk dicek khodam nya**")
        get_name = await client.get_users(user)
        full_name = Extract().getMention(get_name)
    except Exception:
        full_name = Handler().getArg(message)
    logger.get_logger(__name__).info(f"Permintaan mengecek khodam: {full_name}")

    try:
        result = my_api.KhodamCheck(full_name)
        await Handler().sendLongPres(message, result)
        await msg.delete()
        logger.get_logger(__name__).info(f"Berhasil mendapatkan info khodam: {full_name}")
    except FloodWait as e:
        await asyncio.sleep(e.x)  # Wait for the required time before retrying
    except Exception as e:
        await Handler().sendLongPres(message, f"Terjadi kesalahan: {str(e)}")
        await msg.delete()
        logger.get_logger(__name__).error(f"Terjadi kesalahan: {str(e)}")

@app.on_message(filters.command("image"))
async def handle_image(client, message):
    msg = await message.reply("**Silahkan tunggu sebentar...**")
    genBingAi = ImageGen()

    prompt = Handler().getArg(message)
    if not prompt:
        return await msg.edit("/image (prompt text)")

    logger.get_logger(__name__).info(f"Memproses permintaan gambar: {prompt}")

    try:
        image = genBingAi.generate(prompt)
        await client.send_photo(message.chat.id, image, caption=prompt)
        await msg.delete()
        logger.get_logger(__name__).info("Mengirim gambar berhasil.")
    except FloodWait as e:
        await asyncio.sleep(e.x)  # Wait for the required time before retrying
    except Exception as e:
        await msg.edit(f"Terjadi kesalahan: {str(e)}")
        await msg.delete()
        logger.get_logger(__name__).error(f"Error generating image: {e}")

if __name__ == "__main__":
    app.run()
