import asyncio
import os
import random
import sys
import traceback
from io import StringIO
from time import time

from dotenv import load_dotenv
from mytools import Api, BinaryEncryptor, Button, Extract, Handler, ImageGen, LoggerHandler, Translate
from pyrogram import Client, emoji, filters
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
GROUP_ID = os.getenv("GROUP_ID")# Tambahkan ID grup sebagai variabel lingkungan
owner = os.getenv("OWNER_ID")

app = Client(name=BOT_TOKEN.split(":")[0], api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

chatbot_enabled, chat_tagged = {}, []
my_api = Api(name=BOT_NAME, dev=DEV_NAME)
trans = Translate()
binary = BinaryEncryptor(1945)

@app.on_message(filters.command("update") & filters.user(owner))
async def handle_update(client, message):
    await message.reply_text(
        "✨ **Chatbot telah diperbarui!** \n\n"
        "🚀 Fitur-fitur baru telah ditambahkan untuk meningkatkan pengalaman Anda. \n"
        "🤖 Sekarang chatbot bisa memberikan jawaban yang lebih cepat dan akurat! \n\n"
        "Silakan coba dan beri tahu kami jika ada saran atau masukan. \n"
        "Terima kasih telah menggunakan bot kami! 🙏"
    )
    logger.get_logger(__name__).info("Mengirim pesan pembaruan ke pengguna")

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    # Memeriksa apakah pengguna sudah bergabung dengan grup
    try:
        member = await client.get_chat_member(GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            # Jika sudah bergabung, kirim pesan selamat datang
            keyboard = [
                {"text": "Developer", "url": "https://t.me/chakszzz"},
                {"text": "Channel", "url": "https://t.me/ZeebSupport"},
                {"text": "Ubot?", "url": "https://t.me/erprembot"},
            ]
            reply_markup = Button().generateInlineButtonGrid(keyboard)

            await message.reply_text(
                f"**👋 Hai {Extract().getMention(message.from_user)}!**\n"
                "Kenalin nih, gue bot pintar berbasis Python dari mytoolsID. Gue siap bantu jawab semua pertanyaan lo.\n\n"
                "Mau aktifin bot? Ketik aja /chatbot on atau gunakan /update untuk melihat fitur baru! ✨\n\n"
                "Lu bisa make bot-nya di grup lo ya. Masih project Balu."
            )
            logger.get_logger(__name__).info("Mengirim pesan selamat datang")
        else:
            await message.reply_text(
                "🔒 **Maaf, kamu harus bergabung dengan grup berikut untuk menggunakan bot ini:**\n"
                f"[Bergabung di sini](https://t.me/joinchat/{GROUP_ID})"
            )
    except Exception as e:
        await message.reply_text("🔒 **Maaf, kamu harus bergabung dengan grup berikut untuk menggunakan bot ini:**\n"
                                  f"[Bergabung di sini](https://t.me/joinchat/{GROUP_ID})")
        logger.get_logger(__name__).error(f"Terjadi kesalahan saat memeriksa keanggotaan grup: {str(e)}")

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

@app.on_message(filters.command("chatbot"))
async def handle_chatbot(client, message):
    command = message.text.split()[1].lower() if len(message.text.split()) > 1 else ""

    if command == "on":
        chatbot_enabled[message.from_user.id] = True
        await message.reply_text(f"🤖 Chatbot telah diaktifkan untuk {Extract().getMention(message.from_user)}.")
        logger.get_logger(__name__).info(f"Chatbot diaktifkan untuk {Extract().getMention(message.from_user)}")
    elif command == "off":
        chatbot_enabled[message.from_user.id] = False
        await message.reply_text(f"🚫 Chatbot telah dinonaktifkan untuk {Extract().getMention(message.from_user)}.")
        logger.get_logger(__name__).info(f"Chatbot dinonaktifkan untuk {Extract().getMention(message.from_user)}")
    else:
        await message.reply_text("❓ Perintah tidak dikenal. Gunakan /chatbot on atau /chatbot off.")

@app.on_message(filters.command("clear"))
async def handle_clear_message(client, message):
    clear = my_api.clear_chat_history(message.from_user.id)
    await message.reply(clear)

@app.on_message(
    filters.text
    & ~filters.bot
    & ~filters.me
    & ~filters.command(
        ["start", "chatbot", "image", "tagall", "cancel", "clear", "khodam", "tts", "tr", "bencode", "bdecode", "eval"]
    )
)
async def handle_message(client, message):
    if not chatbot_enabled.get(message.from_user.id, False):
        return

    logger.get_logger(__name__).info(f"Menerima pesan dari pengguna dengan ID: {message.from_user.id}")

    await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        result = my_api.ChatBot(message)
        logger.get_logger(__name__).info("Mengirim output besar ke pengguna")
        await Handler().sendLongPres(message, result)
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
    except Exception as e:
        await msg.edit(f"Terjadi kesalahan: {str(e)}")
        logger.get_logger(__name__).error(f"Terjadi kesalahan saat menghasilkan gambar: {str(e)}")

if __name__ == "__main__":
    app.run()
