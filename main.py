import os
import re
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
)
from deep_translator import GoogleTranslator

# --- ENVIRONMENT CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# --- CHANNEL ROUTING ---
# All 4 source channels → Brey's destination channel
CHANNEL_MAP = {
    -1001785197109: -1003891219488,  # AnabelSignals → BREY TRADING FX VIP
    -1001284268486: -1003891219488,  # EasyForexPips → BREY TRADING FX VIP
    -1003745031724: -1003891219488,  # Golden"HardScalping"Room → BREY TRADING FX VIP
    -1003189185116: -1003891219488,  # Golden"Daytrading"Room → BREY TRADING FX VIP
}

# --- NAMES/WATERMARKS TO REMOVE ---
NAMES_TO_REMOVE = [
    r"Anabel\s*Signals?\s*",
    r"Anabel\s*",
    r"Easy\s*Forex\s*Pips?\s*",
    r"EasyForexPips?\s*",
    r"Easy\s*Forex\s*👑?\s*OFFICIAL\s*CHANNEL\s*",
    r"Easy\s*Forex\s*",
    r"Golden\s*\"?HardScalping\"?\s*Room\s*",
    r"Golden\s*\"?Daytrading\"?\s*Room\s*",
    r"Analisis Heury,?\s*Elián\s*y\s*Jafet\s*[🧠📊🔠]*\s*",
    r"Analisis Heury,?\s*",
    r"Elián\s*y\s*Jafet\s*",
    r"Elián\s*",
    r"Jafet\s*",
    r"Heury\s*",
    r"SCALPING JZ\s*💸?\s*GOLD\s*🌿?\s*",
    r"DAYTRADING JZ\s*💰?\s*GOLD\s*🌿?\s*",
    r"SCALPING JZ\s*🦅?\s*GOLD\s*🏆?\s*",
    r"SCALPING JZ\s*",
    r"DAYTRADING JZ\s*",
    r"t\.me/AnabelSignals\s*",
    r"t\.me/EasyForexPips\s*",
    r"@AnabelSignals\s*",
    r"@EasyForexPips\s*",
    r"@\w+",
]

# --- WORD REPLACEMENTS ---
WORD_REPLACEMENTS = {
    r"VENDER": "SELL",
    r"COMPRAR": "BUY",
    r"Vende\b": "SELL",
    r"Compra\b": "BUY",
}

# --- SIGNATURE ---
SIGNATURE = "\n\n📊 Brey's Signals | @BREYTRADING"

# --- BLOCKED IMAGE PHRASES ---
BLOCKED_IMAGE_PHRASES = [
    r"visionarios",
    r"rendimiento diario",
    r"rendimiento del canal",
    r"beneficio neto",
    r"tasa de ganancia",
    r"reporte",
    r"resultado",
    r"canal vip",
    r"participantes",
    r"review",
    r"testimonial",
    r"subscribe",
    r"suscri",
    r"join",
    r"únete",
    r"promotion",
    r"promo",
]

# --- VALID MESSAGES TO COPY ---
ALLOWED_PATTERNS = [
    r"señal lista",
    r"signal ready",
    r"pendientes",
    r"pending",
    r"vender\b",
    r"comprar\b",
    r"sell\b",
    r"buy\b",
    r"entrar entre",
    r"enter between",
    r"entry",
    r"entrada",
    r"xauusd",
    r"eurusd",
    r"gbpusd",
    r"usdjpy",
    r"xau",
    r"gold",
    r"oro\b",
    r"\bsl\b",
    r"stop loss",
    r"stoploss",
    r"\btp1\b",
    r"\btp2\b",
    r"\btp3\b",
    r"\btp4\b",
    r"\btp\s*\d\b",
    r"take profit",
    r"asegura",
    r"secure",
    r"todo en break",
    r"break even",
    r"breakeven",
    r"break en",
    r"colocar break",
    r"coloquen break",
    r"place break",
    r"poner break",
    r"mover break",
    r"están en break",
    r"en break",
    r"50%",
    r"ganancias",
    r"profit",
    r"pagando",
    r"paying",
    r"dentro\b",
    r"seguimos",
    r"cierra",
    r"close",
    r"razón para",
    r"reason",
    r"patrón",
    r"pattern",
    r"engulfing",
    r"base de",
    r"alcanzado",
    r"hit",
    r"invalidada",
    r"retroceso",
    r"tp.*abierto",
    r"corriendo",
    r"running",
    r"análisis",
    r"analysis",
    r"tendencia",
    r"trend",
    r"impulso",
    r"momentum",
    r"soporte",
    r"support",
    r"resistencia",
    r"resistance",
    r"super entrada",
    r"great entry",
    r"colocar",
    r"coloquen",
    r"que rico",
    r"desde el mejor precio",
]

# --- SYSTEM VARIABLES ---
SETTINGS = {
    "ai_translate": False,
    "target_language": "en",
    "paused": False,
    "custom_replacements": {},
    "blocked_words": [],
}

LANGUAGES = {
    "🇬🇧 English": "en",
    "🇪🇸 Spanish": "es",
    "🇫🇷 French": "fr",
    "🇩🇪 German": "de",
    "🇧🇷 Portuguese": "pt",
    "🇸🇦 Arabic": "ar",
    "🇨🇳 Chinese": "zh",
    "🇷🇺 Russian": "ru",
    "🇮🇹 Italian": "it",
}

print("Starting Brey Trading Signal Bot...")

user_client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH
)
bot_client = TelegramClient(StringSession(), API_ID, API_HASH)


def is_authorized(sender_id):
    return sender_id == OWNER_ID


def is_audio_message(message):
    if not message.media:
        return False
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if hasattr(doc, 'mime_type') and doc.mime_type:
            if doc.mime_type.startswith('audio/'):
                return True
        if hasattr(doc, 'attributes'):
            for attr in doc.attributes:
                if type(attr).__name__ in [
                    'DocumentAttributeAudio',
                    'DocumentAttributeVoice'
                ]:
                    return True
    return False


def is_video_message(message):
    if not message.media:
        return False
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if hasattr(doc, 'mime_type') and doc.mime_type:
            if doc.mime_type.startswith('video/'):
                return True
        if hasattr(doc, 'attributes'):
            for attr in doc.attributes:
                if type(attr).__name__ == 'DocumentAttributeVideo':
                    return True
    return False


def is_photo_message(message):
    return isinstance(message.media, MessageMediaPhoto)


def has_links(text):
    if not text:
        return False
    return bool(re.search(
        r'https?://\S+|t\.me/\S+|www\.\S+',
        text, re.IGNORECASE
    ))


def is_blocked_image(text):
    if not text:
        return False
    for phrase in BLOCKED_IMAGE_PHRASES:
        if re.search(phrase, text, re.IGNORECASE):
            return True
    return False


def is_allowed_message(text):
    if not text:
        return False
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def is_blocked_word_found(text):
    if not text:
        return False
    for word in SETTINGS["blocked_words"]:
        if word.lower() in text.lower():
            return True
    return False


def clean_message(text):
    if not text:
        return text
    for pattern in NAMES_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(
        r'https?://\S+|t\.me/\S+|www\.\S+', '', text
    )
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text)
    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(
            re.escape(old), new, text, flags=re.IGNORECASE
        )
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    if text:
        text = text + SIGNATURE
    return text


def get_language_buttons():
    buttons = []
    row = []
    for lang_name, lang_code in LANGUAGES.items():
        current = "✅ " if lang_code == SETTINGS[
            "target_language"
        ] else ""
        row.append(Button.inline(
            f"{current}{lang_name}",
            f"lang_{lang_code}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([Button.inline("🔙 Back", "back_menu")])
    return buttons


def get_main_menu_buttons():
    translate_status = (
        "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
    )
    pause_label = (
        "▶️ Resume" if SETTINGS["paused"] else "⏸ Pause"
    )
    return [
        [Button.inline(
            f"🌐 Translation: {translate_status}",
            "toggle_translate"
        )],
        [Button.inline("🗣 Change Language", "change_language")],
        [Button.inline(pause_label, "toggle_pause")],
        [Button.inline("📊 Status", "show_status")],
        [Button.inline("📡 Channels", "show_channels")],
        [Button.inline("❌ Close", "close")],
    ]


# -------------------------------------------------------------------
# COMMAND HANDLER
# -------------------------------------------------------------------
@bot_client.on(events.NewMessage(pattern=r'^/'))
async def command_menu(event):
    if not is_authorized(event.sender_id):
        return

    command = event.text.strip().lower()
    full_text = event.text.strip()

    if command == "/start":
        await event.respond(
            "👋 **Welcome to Brey Trading Signal Bot!**\n\n"
            "I automatically copy trading signals from 4 source "
            "channels and post them to "
            "**BREY TRADING FX VIP**.\n\n"
            "Use the buttons below to control the bot.",
            buttons=get_main_menu_buttons()
        )

    elif command == "/menu":
        await event.respond(
            "🎛 **Control Panel:**",
            buttons=get_main_menu_buttons()
        )

    elif command == "/help":
        await event.respond(
            "📋 **Available Commands:**\n\n"
            "**🔧 System:**\n"
            "➡️ `/start` - Welcome + button menu\n"
            "➡️ `/menu` - Show control panel\n"
            "➡️ `/help` - Show all commands\n"
            "➡️ `/status` - Current bot status\n\n"
            "**⏯ Control:**\n"
            "➡️ `/pause` - Pause all copying\n"
            "➡️ `/resume` - Resume copying\n\n"
            "**🌐 Translation:**\n"
            "➡️ `/ai on` - Enable translation\n"
            "➡️ `/ai off` - Disable translation\n"
            "➡️ `/language en` - English\n"
            "➡️ `/language es` - Spanish\n"
            "➡️ `/language fr` - French\n"
            "➡️ `/language de` - German\n"
            "➡️ `/language pt` - Portuguese\n\n"
            "**✏️ Word Management:**\n"
            "➡️ `/addword old:new` - Replace a word\n"
            "➡️ `/removeword word` - Remove replacement\n"
            "➡️ `/wordlist` - Show replacements\n"
            "➡️ `/blockword word` - Block a word\n"
            "➡️ `/unblockword word` - Unblock a word\n"
            "➡️ `/blocklist` - Show blocked words\n\n"
            "**📡 Channels:**\n"
            "➡️ `/channels` - Show channel routing\n"
        )

    elif command == "/status":
        paused = "⏸ PAUSED" if SETTINGS["paused"] else "▶️ RUNNING"
        translate = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.respond(
            f"📊 **Current System Status:**\n\n"
            f"• Bot State: `{paused}`\n"
            f"• Translation: `{translate}`\n"
            f"• Language: `{lang_name}`\n"
            f"• Custom Replacements: "
            f"`{len(SETTINGS['custom_replacements'])}`\n"
            f"• Blocked Words: "
            f"`{len(SETTINGS['blocked_words'])}`\n\n"
            f"📡 **Routing:**\n"
            f"• AnabelSignals → BREY TRADING FX VIP\n"
            f"• EasyForexPips → BREY TRADING FX VIP\n"
            f"• Golden\"HardScalping\"Room → BREY TRADING FX VIP\n"
            f"• Golden\"Daytrading\"Room → BREY TRADING FX VIP"
        )

    elif command == "/pause":
        SETTINGS["paused"] = True
        await event.respond(
            "⏸ **Bot Paused.**\n"
            "Send /resume to restart copying."
        )

    elif command == "/resume":
        SETTINGS["paused"] = False
        await event.respond(
            "▶️ **Bot Resumed.**\n"
            "Copying signals again."
        )

    elif command == "/ai on":
        SETTINGS["ai_translate"] = True
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.respond(
            f"✅ **Translation ON** → `{lang_name}`"
        )

    elif command == "/ai off":
        SETTINGS["ai_translate"] = False
        await event.respond(
            "🛑 **Translation OFF.**\n"
            "Messages keep original language."
        )

    elif command.startswith("/language "):
        lang = command.split("/language ")[1].strip()
        supported = list(LANGUAGES.values())
        if lang in supported:
            SETTINGS["target_language"] = lang
            lang_name = next(
                (k for k, v in LANGUAGES.items() if v == lang),
                lang
            )
            await event.respond(
                f"🌐 **Language set to {lang_name}**\n"
                f"Enable with /ai on"
            )
        else:
            await event.respond(
                f"❌ Unsupported: `{lang}`\n"
                f"Supported: `{', '.join(supported)}`"
            )

    elif full_text.lower().startswith("/addword "):
        try:
            parts = full_text[9:].split(":")
            if len(parts) == 2:
                old_word = parts[0].strip()
                new_word = parts[1].strip()
                SETTINGS["custom_replacements"][old_word] = new_word
                await event.respond(
                    f"✅ **Added:** `{old_word}` → `{new_word}`"
                )
            else:
                await event.respond(
                    "❌ Use: `/addword oldword:newword`"
                )
        except Exception:
            await event.respond(
                "❌ Use: `/addword oldword:newword`"
            )

    elif full_text.lower().startswith("/removeword "):
        word = full_text[12:].strip()
        if word in SETTINGS["custom_replacements"]:
            del SETTINGS["custom_replacements"][word]
            await event.respond(f"✅ **Removed:** `{word}`")
        else:
            await event.respond(f"❌ `{word}` not found.")

    elif command == "/wordlist":
        if SETTINGS["custom_replacements"]:
            replacements = "\n".join(
                [f"• `{k}` → `{v}`"
                 for k, v in SETTINGS[
                     "custom_replacements"
                 ].items()]
            )
            await event.respond(
                f"📝 **Replacements:**\n\n{replacements}"
            )
        else:
            await event.respond(
                "📝 None yet. Use `/addword old:new`"
            )

    elif full_text.lower().startswith("/blockword "):
        word = full_text[11:].strip()
        if word not in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].append(word)
            await event.respond(f"🚫 **Blocked:** `{word}`")
        else:
            await event.respond(f"⚠️ Already blocked.")

    elif full_text.lower().startswith("/unblockword "):
        word = full_text[13:].strip()
        if word in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].remove(word)
            await event.respond(f"✅ **Unblocked:** `{word}`")
        else:
            await event.respond(f"❌ Not in blocked list.")

    elif command == "/blocklist":
        if SETTINGS["blocked_words"]:
            words = "\n".join(
                [f"• `{w}`" for w in SETTINGS["blocked_words"]]
            )
            await event.respond(
                f"🚫 **Blocked Words:**\n\n{words}"
            )
        else:
            await event.respond(
                "✅ None. Use `/blockword word`"
            )

    elif command == "/channels":
        await event.respond(
            "📡 **Channel Routing:**\n\n"
            "**Source 1:** AnabelSignals\n"
            "**Source 2:** EasyForexPips\n"
            "**Source 3:** Golden\"HardScalping\"Room\n"
            "**Source 4:** Golden\"Daytrading\"Room\n\n"
            "**Destination:** BREY TRADING FX VIP\n\n"
            "All 4 sources post to the same destination."
        )


# -------------------------------------------------------------------
# BUTTON HANDLER
# -------------------------------------------------------------------
@bot_client.on(events.CallbackQuery())
async def button_handler(event):
    if not is_authorized(event.sender_id):
        await event.answer("❌ Unauthorized", alert=True)
        return

    data = event.data.decode('utf-8')

    if data == "toggle_translate":
        SETTINGS["ai_translate"] = not SETTINGS["ai_translate"]
        status = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        await event.answer(f"Translation: {status}")
        await event.edit(
            "🎛 **Control Panel:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "change_language":
        await event.edit(
            "🌐 **Select Language:**\n"
            "Choose the language for signal translation:",
            buttons=get_language_buttons()
        )

    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        SETTINGS["target_language"] = lang_code
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == lang_code),
            lang_code
        )
        await event.answer(f"✅ Language: {lang_name}")
        await event.edit(
            f"✅ **Language set to {lang_name}**\n"
            f"Enable translation using the main menu.",
            buttons=get_language_buttons()
        )

    elif data == "toggle_pause":
        SETTINGS["paused"] = not SETTINGS["paused"]
        status = (
            "⏸ PAUSED" if SETTINGS["paused"] else "▶️ RUNNING"
        )
        await event.answer(f"Bot is now {status}")
        await event.edit(
            "🎛 **Control Panel:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "show_status":
        paused = (
            "⏸ PAUSED" if SETTINGS["paused"] else "▶️ RUNNING"
        )
        translate = (
            "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        )
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.answer("Status loaded!")
        await event.edit(
            f"📊 **Current Status:**\n\n"
            f"• State: `{paused}`\n"
            f"• Translation: `{translate}`\n"
            f"• Language: `{lang_name}`\n"
            f"• Custom Replacements: "
            f"`{len(SETTINGS['custom_replacements'])}`\n"
            f"• Blocked Words: "
            f"`{len(SETTINGS['blocked_words'])}`",
            buttons=[[Button.inline("🔙 Back", "back_menu")]]
        )

    elif data == "show_channels":
        await event.answer("Channels loaded!")
        await event.edit(
            "📡 **Channel Routing:**\n\n"
            "**Source 1:** AnabelSignals\n"
            "**Source 2:** EasyForexPips\n"
            "**Source 3:** Golden\"HardScalping\"Room\n"
            "**Source 4:** Golden\"Daytrading\"Room\n\n"
            "**Destination:** BREY TRADING FX VIP\n\n"
            "All 4 sources post to the same destination.",
            buttons=[[Button.inline("🔙 Back", "back_menu")]]
        )

    elif data == "back_menu":
        await event.edit(
            "🎛 **Control Panel:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "close":
        await event.delete()


# -------------------------------------------------------------------
# ALBUM HANDLER
# -------------------------------------------------------------------
@user_client.on(events.Album(chats=list(CHANNEL_MAP.keys())))
async def album_handler(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    for msg in event.messages:
        if is_audio_message(msg) or is_video_message(msg):
            print("⏭️ Skipped album: audio/video")
            return

    caption = None
    has_valid_caption = False
    for msg in event.messages:
        if msg.message:
            if is_blocked_image(msg.message):
                print("⏭️ Skipped album: blocked content")
                return
            if is_allowed_message(msg.message):
                has_valid_caption = True
                caption = clean_message(msg.message)
                break

    if not has_valid_caption:
        print("⏭️ Skipped album: no valid signal caption")
        return

    if SETTINGS["ai_translate"] and caption:
        try:
            translated = GoogleTranslator(
                source='auto',
                target=SETTINGS["target_language"]
            ).translate(caption)
            if translated:
                caption = translated + SIGNATURE
        except Exception as e:
            print(f"Translation error: {e}")

    media_files = [
        msg.media for msg in event.messages
        if is_photo_message(msg)
    ]

    if media_files:
        try:
            await user_client.send_file(
                destination_id,
                media_files,
                caption=caption
            )
            print(f"✅ Album sent → {destination_id}")
        except Exception as e:
            print(f"❌ Album failed: {e}")


# -------------------------------------------------------------------
# SINGLE MESSAGE HANDLER
# -------------------------------------------------------------------
@user_client.on(events.NewMessage(chats=list(CHANNEL_MAP.keys())))
async def replication_engine(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    if event.message.grouped_id:
        return

    if is_audio_message(event.message):
        print("⏭️ Skipped: audio")
        return

    if is_video_message(event.message):
        print("⏭️ Skipped: video")
        return

    raw_text = event.message.message
    has_media = event.message.media is not None
    is_photo = is_photo_message(event.message)

    if not raw_text and not has_media:
        return

    if is_photo:
        if not raw_text:
            print("⏭️ Skipped: photo with no caption")
            return
        if is_blocked_image(raw_text):
            print("⏭️ Skipped: blocked image")
            return
        if not is_allowed_message(raw_text):
            print("⏭️ Skipped: photo not a signal")
            return

    if not has_media:
        if not raw_text:
            return
        if not is_allowed_message(raw_text):
            print("⏭️ Skipped: not allowed")
            return
        if has_links(raw_text):
            print("⏭️ Skipped: has links")
            return
        if is_blocked_word_found(raw_text):
            print("⏭️ Skipped: blocked word")
            return

    final_text = None
    if raw_text:
        final_text = clean_message(raw_text)
        if SETTINGS["ai_translate"] and final_text:
            try:
                translated = GoogleTranslator(
                    source='auto',
                    target=SETTINGS["target_language"]
                ).translate(final_text)
                if translated:
                    final_text = translated + SIGNATURE
            except Exception as e:
                print(f"Translation error: {e}")

    try:
        await user_client.send_message(
            destination_id,
            final_text,
            file=event.message.media if is_photo else None
        )
        print(f"✅ Mirrored: {source_id} → {destination_id}")
    except Exception as delivery_error:
        print(f"❌ Delivery failed: {delivery_error}")


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
async def main():
    await user_client.connect()
    if not await user_client.is_user_authorized():
        print("❌ ERROR: Session string is invalid or expired!")
        return
    print("✅ Userbot (scraper) is live.")

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel is live.")

    print("🚀 Brey Trading Signal Bot is running!")
    print("📡 AnabelSignals → BREY TRADING FX VIP")
    print("📡 EasyForexPips → BREY TRADING FX VIP")
    print("📡 Golden\"HardScalping\"Room → BREY TRADING FX VIP")
    print("📡 Golden\"Daytrading\"Room → BREY TRADING FX VIP")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

asyncio.run(main())
