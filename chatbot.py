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

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

LOGS_GROUP_ID = -1002423575637  # Ganti dengan ID grup logs

@app.on_message(filters.command("start"))
async def start(client, message):
    bot_username = (await client.get_me()).username
    user = message.from_user

    keyboard = [
        [InlineKeyboardButton("Developer", url="https://t.me/chakszzz")],
        [InlineKeyboardButton("Join", url="https://t.me/ZeebSupport")],
        [InlineKeyboardButton("Other Bot", url="https://t.me/pamerdong/128")],
        [InlineKeyboardButton("Add to Group", url=f"https://t.me/{bot_username}?startgroup=true")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"<b>👋 Hai {user.mention}!</b>\nKenalin nih, gue bot pintar berbasis Python dari mytoolsID. "
        "Gue siap bantu jawab semua pertanyaan lo.\n\nLu bisa make bot-nya di grup lo ya. "
        "Masih project Balu.\n\nbtw <b>KALO MO MAKE BOTNYA JANGAN SPAM YA MEK. KALO SPAM GW LAPORIN MAKLO DAH!</b>",
        reply_markup=reply_markup
    )

    # Mengirim pesan log ke grup logs
    await client.send_message(
        LOGS_GROUP_ID,
        f"User {user.mention} dengan ID {user.id} baru saja memulai bot.",
    )
    logger.get_logger(__name__).info("Mengirim pesan selamat datang ke user")

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
SETUJU = [6607703424, 940232666, 1325957770, 1448273246, 5913061784]

whitelisted_groups = set()
blacklisted_groups = set()

MAX_RESPONSE_LENGTH = 5000

# Dictionary untuk melacak status aktif/nonaktif chatbot per grup
chatbot_active_per_group = {}

# Menyimpan informasi mengenai jumlah pesan yang dikirim oleh pengguna dalam waktu tertentu
user_message_count = {}
# Menyimpan status pengguna apakah dianggap sebagai spammer
spammer_users = set()

# Batasan waktu untuk mendeteksi spam (misalnya 10 detik)
spam_time_window = 10

# Batasan jumlah pesan dalam waktu tersebut (misalnya 5 pesan)
spam_message_limit = 5

# Group ID untuk log
  # Ganti dengan ID grup log yang diinginkan

@app.on_message(filters.text & ~filters.bot & ~filters.me & filters.group)
async def handle_message(client, message):
    global chatbot_active_per_group

    text = message.text.lower()
    current_time = time.time()
    user_id = message.from_user.id
    group_id = message.chat.id

    # Jika pengguna belum ada di data, inisialisasi data mereka
    if user_id not in user_message_count:
        user_message_count[user_id] = []

    # Tambahkan waktu pengiriman pesan ke list untuk pengguna ini
    user_message_count[user_id].append(current_time)

    # Hapus pesan lama dari list (yang lebih lama dari waktu window)
    user_message_count[user_id] = [
        timestamp for timestamp in user_message_count[user_id]
        if current_time - timestamp <= spam_time_window
    ]

    # Deteksi spam: jika jumlah pesan dalam waktu tertentu lebih dari batas
    if len(user_message_count[user_id]) > spam_message_limit:
        # Tandai pengguna sebagai spammer
        spammer_users.add(user_id)

        # Kirim peringatan di grup
        await message.reply("<blockquote>🚨 Anda mengirim pesan terlalu cepat. Pesan Anda dianggap sebagai spam dan interaksi Anda dengan bot diblokir sementara.</blockquote>")

        # Kirim peringatan ke logs group
        warning_message = f"Peringatan: {message.from_user.first_name} dianggap sebagai spammer di grup {message.chat.title}."
        await client.send_message(LOGS_GROUP_ID, warning_message)
        return

    # Jika pengguna dianggap sebagai spammer, abaikan pesan mereka
    if user_id in spammer_users:
        return

    # Bagian untuk memproses whitelist/blacklist grup
    if group_id in blacklisted_groups:
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

    # Bagian blacklist dan remove
    if ("blacklist" in text or "block" in text) and message.from_user.id in OWNER_IDS:
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

    # Bagian lain dari logika chatbot tetap sama seperti sebelumnya...
    # ...

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

# Handler untuk perintah /add
@app.on_message(filters.command("add"))
async def handle_add_command(client, message):
    global whitelisted_groups

    text = message.text.lower()

    try:
        # Coba ambil ID grup dari input manual
        group_id_to_add = int(text.split("add")[-1].strip())
    except ValueError:
        # Jika tidak ada input manual, balas dengan error
        await message.reply(f"<blockquote>ID grup tidak valid. Gunakan format: /add <id_group></blockquote>")
        return

    if group_id_to_add in whitelisted_groups:
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} sudah ada di whitelist.</blockquote>")
    else:
        whitelisted_groups.add(group_id_to_add)
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} berhasil ditambahkan ke whitelist.</blockquote>")
        logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_add} ditambahkan ke whitelist.")

# Handler untuk perintah /remove
@app.on_message(filters.command("remove"))
async def handle_remove_command(client, message):
    global whitelisted_groups, blacklisted_groups

    text = message.text.lower()

    try:
        # Coba ambil ID grup dari input manual
        group_id_to_remove = int(text.split("remove")[-1].strip())
    except ValueError:
        await message.reply(f"<blockquote>ID grup tidak valid. Gunakan format: /remove <id_group></blockquote>")
        return

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

# Handler untuk perintah /blacklist
@app.on_message(filters.command("blacklist"))
async def handle_blacklist_command(client, message):
    global blacklisted_groups, whitelisted_groups

    text = message.text.lower()

    try:
        # Coba ambil ID grup dari input manual
        group_id_to_blacklist = int(text.split("blacklist")[-1].strip())
    except ValueError:
        await message.reply(f"<blockquote>ID grup tidak valid. Gunakan format: /blacklist <id_group></blockquote>")
        return

    if group_id_to_blacklist in blacklisted_groups:
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_blacklist} sudah ada di blacklist.</blockquote>")
    else:
        blacklisted_groups.add(group_id_to_blacklist)
        if group_id_to_blacklist in whitelisted_groups:
            whitelisted_groups.remove(group_id_to_blacklist)  # Hapus dari whitelist jika ada
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_blacklist} berhasil diblacklist. Bot tidak akan merespons di grup ini.</blockquote>")
        logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_blacklist} diblacklist.")


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
