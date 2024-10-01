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

if len(sys.argv) < 2:
    print("Error: Harap tentukan file .env sebagai argumen saat menjalankan skrip.")
    sys.exit(1)  # Keluar dari program dengan status error

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
        {"text": "Join", "url": "https://t.me/ZeebSupport"},
        {"text": "Other Bot", "url": "https://t.me/erprembot"},
    ]
    reply_markup = Button().generateInlineButtonGrid(keyboard)

    await message.reply_text(
        f"<blockquote><b>👋 Hai {Extract().getMention(message.from_user)}!</b>\nKenalin nih, gue bot pintar berbasis Python dari mytoolsID. Gue siap bantu jawab semua pertanyaan lo.\n\nLu bisa make bot-nya di grup lo ya. Masih project Balu.\n\nbtw <b>KALO MO MAKE BOTNYA JANGAN SPAM YA MEK. KALO SPAM GW LAPORIN MAKLO DAH!</b></blockquote>",
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
# Di bagian atas kode, ganti dengan daftar ID pemilik bot
OWNER_IDS = [1448273246, 6607703424]
SETUJU = [6607703424, 940232666, 1325957770]

@app.on_message(filters.text & ~filters.bot & ~filters.me & filters.group)
async def handle_message(client, message):
    global chatbot_active

    text = message.text.lower()
    if "aktif" in text or "syalala" in text:
        if message.from_user.id not in SETUJU:
            await message.reply(f"<blockquote>lo siapa 🗿.</blockquote>")
            return

        try:
            chatbot_active = True
            await message.reply("<blockquote>Chatbot sekarang <b>aktif</b>! 🎉</blockquote>")
            logger.get_logger(__name__).info("Chatbot Aktif.")
        except Exception as e:
            await message.reply(f"Terjadi kesalahan saat mengaktifkan chatbot: {e} ⚠️")
            logger.error(f"Error saat mengaktifkan chatbot: {e}")
        return
    elif "nonaktif" in text or "cukup" in text:
        if message.from_user.id not in SETUJU:
            await message.reply(f"<blockquote>lo siapa 🗿.</blockquote>")
            return

        try:
            chatbot_active = False
            await message.reply("<blockquote>Chatbot sekarang <b>non-aktif❌</blockquote>")
            logger.get_logger(__name__).info("Chatbot dinonaktifkan.")
        except Exception as e:
            await message.reply(f"Terjadi kesalahan saat menonaktifkan chatbot: {e} ⚠️")
            logger.error(f"Error saat menonaktifkan chatbot: {e}")
        return

    if "update" in text:
        if message.from_user.id not in OWNER_IDS:
            await message.reply(f"<blockquote>Anda tidak memiliki izin untuk melakukan pembaruan 🗿.</blockquote>")
            return

        logger.get_logger(__name__).info("Memulai proses update bot.")
        try:
            pros = await message.reply(
                f"<i><blockquote>🔄 {app.me.mention} Sedang memeriksa pembaruan...</blockquote></i>"
            )
            out = subprocess.check_output(["git", "pull"]).decode("UTF-8")

            if "Already up to date." in str(out):
                return await pros.edit(
                    f"<blockquote>✅ {app.me.mention} sudah terbaru.</blockquote>"
                )

            await pros.edit(
                f"<blockquote>🔄 Pembaruan berhasil! Bot telah diperbarui. 🚀</blockquote>"
            )

            subprocess.run(["start", "1"], shell=True)

        except Exception as e:
            await message.reply(f"Terjadi kesalahan saat memperbarui: {e} ⚠️")
            logger.error(f"Error saat memperbarui bot: {e}")

        return

    current_time = time.time()
    last_response_time = user_last_response_time[message.from_user.id]

    if current_time - last_response_time < response_cooldown:
        return

    user_last_response_time[message.from_user.id] = current_time

    if not chatbot_active:  
        return

    logger.get_logger(__name__).info(f"Menerima pesan dari pengguna dengan ID: [{message.from_user.id}]")

    await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        result = my_api.ChatBot(message)
        format_result = f"<blockquote>{result}</blockquote>"
        logger.get_logger(__name__).info("Mengirim output besar ke pengguna")
        await Handler().sendLongPres(message, format_result)
    except FloodWait as e:
        await asyncio.sleep(e.x)  # Wait for the required time before retrying
    except Exception as e:
        await Handler().sendLongPres(message, f"Terjadi kesalahan: {str(e)} ⚠️")
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
