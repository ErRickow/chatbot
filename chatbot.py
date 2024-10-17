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
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

if len(sys.argv) < 2:
    print("Error: Harap tentukan file .env sebagai argumen saat menjalankan skrip.")
    sys.exit(1) 

OWNER_IDS = [1448273246]
SETUJU = [6607703424, 940232666, 1325957770, 1448273246, 5913061784]

whitelisted_groups = set()
blacklisted_groups = set()

MAX_RESPONSE_LENGTH = 5000

# Dictionary untuk melacak status aktif/nonaktif chatbot per grup
chatbot_active_per_group = {}

user_message_count = {}

spammer_users = set()

spam_time_window = 10

spam_message_limit = 5

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

LOGS_GROUP_ID = -1002423575637  # Ganti dengan ID grup logs

REQUIRED_CHANNELS = [
    {"name": "ZeebSupport", "link": "https://t.me/ZeebSupport"},
    {"name": "ErSupport", "link": "https://t.me/Er_support_group"},
]

@app.on_message(filters.command("start"))
async def start(client, message):
    bot_username = (await client.get_me()).username
    user = message.from_user
    user_id = user.id

    if user_id not in OWNER_IDS:
        not_joined_channels = []

        for channel in REQUIRED_CHANNELS:
            try:
                # Memeriksa apakah user adalah anggota channel
                member = await client.get_chat_member(channel["name"], user_id)

                # Jika bukan anggota atau belum join, tambahkan ke daftar not_joined_channels
                if member.status not in ["member", "administrator", "creator"]:
                    not_joined_channels.append(channel)

            except Exception as e:
                # Tangani error dengan mengirim pesan ke logs group
                await client.send_message(
                    LOGS_GROUP_ID,
                    f"Error dalam pengecekan channel {channel['name']} untuk user {user.mention} dengan ID {user.id}: {e}"
                )
                not_joined_channels.append(channel)

        # Jika ada channel yang belum diikuti, kirim pesan untuk meminta user bergabung
        if not_joined_channels:
            await message.reply_text(
                f"<b>Hai {user.mention}!</b>\n"
                f"Untuk menggunakan bot ini, silakan join ke semua channel berikut:\n"
                + "\n".join([f"- [{ch['name']}]({ch['link']})" for ch in not_joined_channels]),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Join {ch['name']}", url=ch["link"]) for ch in not_joined_channels]
                ]),
                disable_web_page_preview=True
            )
            return

    # Jika pengguna adalah pemilik bot atau sudah bergabung di semua channel, lanjutkan dengan pesan selamat datang
    keyboard = [
        [InlineKeyboardButton("Developer", url="https://t.me/chakszzz"),
         InlineKeyboardButton("Support", url="https://t.me/Er_Support_Group")],
        [InlineKeyboardButton("Other Bot", url="https://t.me/pamerdong/128"),
         InlineKeyboardButton("Add to Group", url=f"https://t.me/{bot_username}?startgroup=true")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"<b>👋 Halo {user.mention}!</b>\n"
        "Kenalin, gue adalah asisten virtual cerdas yang selalu siap membantu lo! Dari pertanyaan simpel sampai yang rumit, gue punya jawabannya. "
        "Gue udah diprogram untuk ngasih respon yang cepat dan akurat.\n\n"
        "Ayo coba ajak gue ke grup lo, biar obrolan jadi lebih seru dan informatif! Tapi inget, <b>hindari spam ya! Kalau spam, gue nggak segan-segan laporin ke admin!</b>",
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

@app.on_message(filters.command("white"))
async def handle_add_command(client, message):
    global whitelisted_groups

    text = message.text.lower()

    try:
        group_id_to_add = int(text.split("add")[-1].strip())
    except ValueError:
        await message.reply(f"<blockquote>ID grup tidak valid. Gunakan format: /add <id_group></blockquote>")
        return

    if group_id_to_add in whitelisted_groups:
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} sudah ada di whitelist.</blockquote>")
    else:
        whitelisted_groups.add(group_id_to_add)
        await message.reply(f"<blockquote>Grup dengan ID {group_id_to_add} berhasil ditambahkan ke whitelist.</blockquote>")
        logger.get_logger(__name__).info(f"Grup dengan ID {group_id_to_add} ditambahkan ke whitelist.")

@app.on_message(filters.command("rem"))
async def handle_remove_command(client, message):
    global whitelisted_groups, blacklisted_groups

    text = message.text.lower()

    try:
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

@app.on_message(filters.command("bl"))
async def handle_blacklist_command(client, message):
    global blacklisted_groups, whitelisted_groups

    text = message.text.lower()

    try:
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
