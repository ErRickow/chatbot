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
    sys.exit(1) 

load_dotenv(sys.argv[1])

logger = LoggerHandler()
logger.setup_logger()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
DEV_NAME = os.getenv("DEV_NAME")

app = Client(name=BOT_TOKEN.split(":")[0], api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

chatbot_active = False  
user_last_response_time = defaultdict(lambda: 0)
response_cooldown = 0.5
my_api = Api(name=BOT_NAME, dev=DEV_NAME)
trans = Translate()
binary = BinaryEncryptor(1945)

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    keyboard = [
        {"text": "Developer", "url": "https://t.me/chakszzz"},
        {"text": "visit", "url": "https://t.me/ZeebSupport"},
        {"text": "Other Bot", "url": "https://t.me/erprembot"},
        {"text": "visit here too", "url": "https://t.me/"}, 
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

OWNER_IDS = [1448273246, 6607703424]
SETUJU = [6607703424, 940232666, 1325957770, 1448273246]

whitelisted_groups = set()
blacklisted_groups = set()

MAX_RESPONSE_LENGTH = 5000

# Dictionary untuk melacak status aktif/nonaktif chatbot per grup
chatbot_active_per_group = {}

@app.on_message(filters.text & ~filters.bot & ~filters.me & filters.group)
async def handle_message(client, message):
    global chatbot_active_per_group

    text = message.text.lower()
    current_time = time.time()

    if message.from_user.id not in user_last_response_time:
        user_last_response_time[message.from_user.id] = 0

    last_response_time = user_last_response_time[message.from_user.id]

    if current_time - last_response_time < response_cooldown:
        return

    user_last_response_time[message.from_user.id] = current_time

    group_id = message.chat.id

    if group_id in blacklisted_groups:
        logger.get_logger(__name__).info(f"Pesan diabaikan, grup {message.chat.title} ada di blacklist.")
        return

    if group_id not in whitelisted_groups and "add" not in text:
        return

    # Bagian 'add' yang telah diperbarui dengan input ID manual
    if "add" in text and message.from_user.id in OWNER_IDS:
        try:
            # Coba ambil ID grup dari input manual
            group_id_to_add = int(text.split("add")[-1].strip())
        except ValueError:
            # Jika tidak ada input manual, gunakan ID grup saat ini
            group_id_to_add = group_id

        if group_id_to_add in whitelisted_groups:
            await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} sudah ada di whitelist.</blockquote>")
        else:
            whitelisted_groups.add(group_id_to_add)
            await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} berhasil ditambahkan ke whitelist.</blockquote>")
            logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_add} ditambahkan ke whitelist.")
        return

    if ("blacklist" in text or "bl" in text) and message.from_user.id in OWNER_IDS:
        if group_id in blacklisted_groups:
            await message.reply(f"<blockquote>Grup {message.chat.title} sudah ada di blacklist.</blockquote>")
        else:
            blacklisted_groups.add(group_id)
            if group_id in whitelisted_groups:
                whitelisted_groups.remove(group_id)
            await message.reply(f"<blockquote>Grup {message.chat.title} berhasil diblacklist. Bot tidak akan merespons di grup ini.</blockquote>")
            logger.get_logger(__name__).info(f"Grup {message.chat.title} diblacklist.")
        return

    if "remove" in text and message.from_user.id in OWNER_IDS:
        try:
            group_id_to_remove = int(text.split("remove")[-1].strip())

            if group_id_to_remove in whitelisted_groups:
                whitelisted_groups.remove(group_id_to_remove)
                await message.reply(f"<blockquote>Grup dengan ID {group_id_to_remove} berhasil dihapus dari whitelist.</blockquote>")
                logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_remove} dihapus dari whitelist.")
            elif group_id_to_remove in blacklisted_groups:
                blacklisted_groups.remove(group_id_to_remove)
                await message.reply(f"<blockquote>Grup dengan ID {group_id_to_remove} berhasil dihapus dari blacklist.</blockquote>")
                logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_remove} dihapus dari blacklist.")
            else:
                await message.reply(f"<blockquote>Grup dengan ID {group_id_to_remove} tidak ditemukan di whitelist atau blacklist.</blockquote>")
        except ValueError:
            await message.reply(f"<blockquote>ID grup tidak valid. Gunakan format: /remove <id_group></blockquote>")
        return

    if "list" in text and message.from_user.id in OWNER_IDS:
        whitelisted_list = "\n".join([str(gid) for gid in whitelisted_groups]) or "Tidak ada grup dalam whitelist."
        blacklisted_list = "\n".join([str(gid) for gid in blacklisted_groups]) or "Tidak ada grup dalam blacklist."
        
        await message.reply(f"<blockquote><b>Grup Whitelist:</b>\n{whitelisted_list}\n\n<b>Grup Blacklist:</b>\n{blacklisted_list}</blockquote>")
        return

    if "aktif" in text or "syalala" in text:
        if message.from_user.id not in SETUJU:
            await message.reply(f"<blockquote>lo siapa 🗿.</blockquote>")
            return

        try:
            chatbot_active_per_group[group_id] = True  # Aktifkan hanya untuk grup ini
            await message.reply(f"<blockquote>{app.me.mention} sekarang <b>🎉 aktif</b> di grup {message.chat.title}</blockquote>")
            logger.get_logger(__name__).info(f"Chatbot aktif di grup {message.chat.title}.")
        except Exception as e:
            await message.reply(f"<blockquote>Terjadi kesalahan saat mengaktifkan chatbot: {e} ⚠️</blockquote>")
            logger.error(f"Error saat mengaktifkan chatbot: {e}")
        return

    elif "diam" in text or "cukup" in text:
        if message.from_user.id not in SETUJU:
            await message.reply(f"<blockquote>lo siapa 🗿.</blockquote>")
            return

        try:
            chatbot_active_per_group[group_id] = False  # Nonaktifkan hanya untuk grup ini
            await message.reply(f"<blockquote>{app.me.mention} sekarang <b>❌ non-aktif di grup {message.chat.title}</blockquote>")
            logger.get_logger(__name__).info(f"Chatbot dinonaktifkan di grup {message.chat.title}.")
        except Exception as e:
            await message.reply(f"<blockquote>Terjadi kesalahan saat menonaktifkan chatbot: {e} ⚠️</blockquote>")
            logger.error(f"Error saat menonaktifkan chatbot: {e}")
        return

    # Jika chatbot non-aktif untuk grup ini, tidak akan merespon
    if not chatbot_active_per_group.get(group_id, False):
        return

    # Jika pengguna mereply pengguna lain, bot tidak merespons, tetapi jika pengguna mereply bot, bot merespons
    if message.reply_to_message:
        if message.reply_to_message.from_user.id != app.me.id:
            return  # Pengguna mereply pengguna lain, jadi bot tidak merespons

    try:
        await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        
        result = my_api.ChatBot(message)

        if len(result) > MAX_RESPONSE_LENGTH:
            result = result[:MAX_RESPONSE_LENGTH] + "\n\n[Response truncated...]"

        await message.reply(f"<blockquote>{result}</blockquote>", quote=True)
    
    except Exception as e:
        await message.reply(f"<blockquote>Terjadi kesalahan: {str(e)} ⚠️</blockquote>")
        logger.get_logger(__name__).error(f"Terjadi kesalahan: {str(e)}")

    return

    # Bagian khodam yang diminta
    if "khodam" in text:
        try:
            msg = await message.reply("**Sedang memproses....**")

            user = await Extract().getId(message)
            if not user:
                return await msg.edit("**Harap berikan username atau reply ke pengguna untuk dicek khodam nya.**")

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
        await asyncio.sleep(e.x)
    except Exception as e:
        logger.get_logger(__name__).error(f"Error generating {command}: {e}")
        await msg.edit(f"Error: {str(e)}")

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
