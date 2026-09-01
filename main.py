import os
import re
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
)
from telethon.errors import (
    SessionExpiredError,
    SessionRevokedError,
    AuthKeyUnregisteredError,
)

# --- ENVIRONMENT CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# --- CHANNEL ROUTING ---
SOURCE_CHANNEL = -1003357855905
DESTINATION_CHANNEL = -1003891219488

CHANNEL_MAP = {
    SOURCE_CHANNEL: DESTINATION_CHANNEL,
}

# --- NAMES/WATERMARKS TO REMOVE ---
NAMES_TO_REMOVE = [
    r"Switzy\s*VIP\s*Gold\s*",
    r"Switzy\s*Personal\s*",
    r"Switzy\s*",
    r"@\w+",
    r"t\.me/\S+",
    r"https?://\S+",
    r"www\.\S+",
]

# --- WORD REPLACEMENTS ---
WORD_REPLACEMENTS = {
    r"\bVENDER\b": "SELL",
    r"\bCOMPRAR\b": "BUY",
    r"\bVende\b": "SELL",
    r"\bCompra\b": "BUY",
}

# --- SIGNATURE ---
SIGNATURE = "\n\n📊 Brey's Signals | @BREYTRADING"

# --- ERROR TEXTS TO STRIP FROM MESSAGES ---
ERROR_TEXTS_TO_REMOVE = [
    r"Error\s*500\s*\(Server Error\)[^\n]*",
    r"That'?s an error\.[^\n]*",
    r"There was an error\.[^\n]*",
    r"Please try again later\.[^\n]*",
    r"That'?s all we know\.[^\n]*",
    r"Error\s*\d+[^\n]*",
    r"Server Error[^\n]*",
    r"HTTP Error[^\n]*",
    r"Connection Error[^\n]*",
    r"Request Failed[^\n]*",
    r"Timed out[^\n]*",
]

# --- BLOCKED CONTENT ---
BLOCKED_PHRASES = [
    r"join (our|my|the)?\s*(free|vip|premium|channel)",
    r"click (the|this)?\s*link",
    r"subscribe",
    r"t\.me/\+",
    r"joinchat",
    r"contact (us|me|admin)",
    r"dm (us|me)",
    r"reach out",
    r"free signals",
    r"señales gratis",
    r"únete",
    r"registro gratis",
    r"register",
    r"whatsapp",
    r"instagram",
    r"facebook",
    r"youtube",
    r"website",
    r"discount",
    r"descuento",
    r"promotion",
    r"promo",
    r"refer",
    r"invite",
    r"meta\s*(ads|business|campaign)",
    r"facebook\s*ads",
    r"campaña",
    r"anuncio",
    r"conjunto de anuncios",
    r"rechazamos tu anuncio",
    r"errores de conjuntos",
    r"puntuación de oportunidad",
    r"resultado potencial",
    r"nueva campaña",
    r"suscripcion.*sitio web",
    r"costo por",
    r"entrega activada",
    r"revisar.*anuncio",
    r"switzy",
    r"envíen sus ganancias",
    r"envien sus ganancias",
    r"manda.*ganancias",
    r"send.*ganancias",
    r"500\s*[£€$]",
    r"like.*publicacion",
    r"like.*publication",
    r"dale like",
    r"ganen.*dinero",
    r"ganar dinero",
    r"nuevos servicios",
    r"new services",
    r"acceso.*bot",
    r"abriendo.*acceso",
    r"opening.*access",
    r"palabra.*bot",
    r"enviar.*bot",
    r"envíen.*mensaje",
    r"envien.*mensaje",
    r"\bchicos\b",
    r"dos cosas",
    r"ahora mismo estoy",
    r"mensaje.*palabra",
    r"para acceder",
    r"todo lo que tienen que hacer",
    r"todo lo que tienes que hacer",
]

# --- VALID GOLD SIGNAL PATTERNS ---
GOLD_SIGNAL_PATTERNS = [
    r"\bxauusd\b",
    r"\bxau/usd\b",
    r"\bxau\b",
    r"\bgold\b",
    r"\boro\b",
    r"\bsell\b",
    r"\bbuy\b",
    r"\bvender\b",
    r"\bcomprar\b",
    r"\btp1\b",
    r"\btp2\b",
    r"\btp3\b",
    r"\btp4\b",
    r"\btp\s*\d\b",
    r"take profit",
    r"\bsl\b",
    r"stop loss",
    r"entrar entre",
    r"\bentry\b",
    r"\bentrada\b",
    r"break even",
    r"breakeven",
    r"break en",
    r"colocar break",
    r"coloquen break",
    r"\basegura\b",
    r"\bsecure\b",
    r"señal lista",
    r"signal ready",
    r"\bpendientes\b",
    r"\bpips\b",
    r"\bscalp\b",
    r"\bsoporte\b",
    r"\bresistencia\b",
    r"\btendencia\b",
    r"\banálisis\b",
    r"\balcanzado\b",
    r"\binvalidada\b",
    r"\bcorriendo\b",
    r"\bseguimos\b",
    r"\bcierra\b",
    r"\bdentro\b",
    r"\bpagando\b",
    r"close.*position",
    r"trail.*sl",
    r"second entry",
    r"maximize profit",
    r"primera entrada",
    r"primera entr",
    r"50%",
]

# --- SYSTEM VARIABLES ---
SETTINGS = {
    "ai_translate": False,
    "target_language": "es",
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


# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
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


def is_noforwards(message):
    return getattr(message, 'noforwards', False)


def is_promotional(text):
    if not text:
        return False
    for pattern in BLOCKED_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"🚫 Blocked: {pattern}")
            return True
    return False


def is_valid_signal(text):
    if not text:
        return False
    for pattern in GOLD_SIGNAL_PATTERNS:
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


def remove_error_texts(text):
    """Strip error messages from source channel posts."""
    if not text:
        return text
    for pattern in ERROR_TEXTS_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def clean_message(text):
    """Remove names, links, errors. No translation."""
    if not text:
        return text
    text = remove_error_texts(text)
    for pattern in NAMES_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(
        r'https?://\S+|t\.me/\S+|www\.\S+|joinchat/\S+',
        '', text
    )
    text = re.sub(r'@\w+', '', text)
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(
            pattern, replacement, text, flags=re.IGNORECASE
        )
    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(
            re.escape(old), new, text, flags=re.IGNORECASE
        )
    text = re.sub(
        r'\bxauusd\b', 'XAUUSD', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\bxau/usd\b', 'XAU/USD', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\btp(\d)\b', r'TP\1', text, flags=re.IGNORECASE
    )
    text = re.sub(r'\bsl\b', 'SL', text, flags=re.IGNORECASE)
    lines = text.split('\n')
    cleaned_lines = [
        line for line in lines
        if line.strip() and not re.match(
            r'^[\s\-_•|/\\:.]+$', line.strip()
        )
    ]
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def process_message(raw_text):
    """Clean → remove errors → sign."""
    if not raw_text:
        return None
    text = clean_message(raw_text)
    if not text:
        return None
    return text + SIGNATURE


# -------------------------------------------------------------------
# MENU HELPERS
# -------------------------------------------------------------------
def get_language_buttons():
    buttons = []
    row = []
    for lang_name, lang_code in LANGUAGES.items():
        current = "✅ " if lang_code == SETTINGS[
            "target_language"
        ] else ""
        row.append(Button.inline(
            f"{current}{lang_name}", f"lang_{lang_code}"
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
    lang_name = next(
        (k for k, v in LANGUAGES.items()
         if v == SETTINGS["target_language"]),
        SETTINGS["target_language"]
    )
    return [
        [Button.inline(
            f"🌐 Translation: {translate_status}",
            "toggle_translate"
        )],
        [Button.inline(
            f"🗣 Language: {lang_name}",
            "change_language"
        )],
        [Button.inline(pause_label, "toggle_pause")],
        [Button.inline("📊 Status", "show_status")],
        [Button.inline("📡 Channels", "show_channels")],
        [Button.inline("❌ Close", "close")],
    ]


async def safe_edit(event, text, buttons=None):
    try:
        if buttons:
            await event.edit(text, buttons=buttons)
        else:
            await event.edit(text)
    except Exception as e:
        if "not modified" in str(e).lower():
            pass
        else:
            print(f"Edit error: {e}")


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
            "👋 **Bienvenido a Brey Trading Signal Bot!**\n\n"
            "📡 Copiando señales de Gold automáticamente\n"
            "➡️ Destino: **BREY TRADING FX VIP**\n\n"
            "🚫 Mensajes promocionales: **Bloqueados**\n"
            "🚫 Textos de error: **Eliminados**\n"
            "📋 Señales: **Copiadas limpiamente**\n\n"
            "Usa los botones para controlar el bot.",
            buttons=get_main_menu_buttons()
        )

    elif command == "/menu":
        await event.respond(
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif command == "/help":
        await event.respond(
            "📋 **Comandos:**\n\n"
            "➡️ `/start` - Bienvenida\n"
            "➡️ `/menu` - Panel de control\n"
            "➡️ `/status` - Estado actual\n"
            "➡️ `/pause` - Pausar bot\n"
            "➡️ `/resume` - Reanudar bot\n"
            "➡️ `/ai on` - Activar traducción\n"
            "➡️ `/ai off` - Desactivar traducción\n"
            "➡️ `/language es` - Español\n"
            "➡️ `/language en` - Inglés\n"
            "➡️ `/addword vieja:nueva` - Reemplazar\n"
            "➡️ `/removeword palabra` - Quitar\n"
            "➡️ `/wordlist` - Ver reemplazos\n"
            "➡️ `/blockword palabra` - Bloquear\n"
            "➡️ `/unblockword palabra` - Desbloquear\n"
            "➡️ `/blocklist` - Ver bloqueadas\n"
            "➡️ `/channels` - Ver canales\n"
            "➡️ `/ping` - Verificar bot activo\n"
        )

    elif command == "/status":
        paused = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        translate = (
            "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        )
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.respond(
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `{translate}`\n"
            f"• Idioma: `{lang_name}`\n"
            f"• Canal fuente: `{SOURCE_CHANNEL}`\n"
            f"• Canal destino: `{DESTINATION_CHANNEL}`\n"
            f"• Reemplazos: "
            f"`{len(SETTINGS['custom_replacements'])}`\n"
            f"• Palabras bloqueadas: "
            f"`{len(SETTINGS['blocked_words'])}`\n\n"
            f"✅ Bot funcionando correctamente"
        )

    elif command == "/ping":
        await event.respond(
            "🏓 **Pong!**\n"
            "✅ Bot activo y funcionando.\n"
            f"📡 Monitoreando: `{SOURCE_CHANNEL}`"
        )

    elif command == "/pause":
        SETTINGS["paused"] = True
        await event.respond("⏸ **Bot Pausado.**")

    elif command == "/resume":
        SETTINGS["paused"] = False
        await event.respond(
            "▶️ **Bot Reanudado.**\n"
            "📡 Copiando señales nuevamente."
        )

    elif command == "/ai on":
        SETTINGS["ai_translate"] = True
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.respond(
            f"✅ **Traducción ACTIVADA** → `{lang_name}`"
        )

    elif command == "/ai off":
        SETTINGS["ai_translate"] = False
        await event.respond("🛑 **Traducción DESACTIVADA.**")

    elif command.startswith("/language "):
        lang = command.split("/language ")[1].strip()
        if lang in LANGUAGES.values():
            SETTINGS["target_language"] = lang
            lang_name = next(
                (k for k, v in LANGUAGES.items() if v == lang),
                lang
            )
            await event.respond(
                f"🌐 **Idioma: {lang_name}**"
            )
        else:
            await event.respond(
                f"❌ No soportado: `{lang}`\n"
                f"Opciones: en, es, fr, de, pt, ar, zh, ru, it"
            )

    elif full_text.lower().startswith("/addword "):
        try:
            parts = full_text[9:].split(":")
            if len(parts) == 2:
                old_word = parts[0].strip()
                new_word = parts[1].strip()
                SETTINGS["custom_replacements"][old_word] = new_word
                await event.respond(
                    f"✅ `{old_word}` → `{new_word}`"
                )
            else:
                await event.respond(
                    "❌ Usa: `/addword palabravieja:nuevapalabra`"
                )
        except Exception:
            await event.respond(
                "❌ Usa: `/addword palabravieja:nuevapalabra`"
            )

    elif full_text.lower().startswith("/removeword "):
        word = full_text[12:].strip()
        if word in SETTINGS["custom_replacements"]:
            del SETTINGS["custom_replacements"][word]
            await event.respond(f"✅ Eliminado: `{word}`")
        else:
            await event.respond(f"❌ `{word}` no encontrado.")

    elif command == "/wordlist":
        if SETTINGS["custom_replacements"]:
            replacements = "\n".join(
                [f"• `{k}` → `{v}`"
                 for k, v in SETTINGS[
                     "custom_replacements"
                 ].items()]
            )
            await event.respond(
                f"📝 **Reemplazos:**\n\n{replacements}"
            )
        else:
            await event.respond(
                "📝 Ninguno. Usa `/addword vieja:nueva`"
            )

    elif full_text.lower().startswith("/blockword "):
        word = full_text[11:].strip()
        if word not in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].append(word)
            await event.respond(f"🚫 Bloqueado: `{word}`")
        else:
            await event.respond(f"⚠️ Ya bloqueado.")

    elif full_text.lower().startswith("/unblockword "):
        word = full_text[13:].strip()
        if word in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].remove(word)
            await event.respond(f"✅ Desbloqueado: `{word}`")
        else:
            await event.respond(f"❌ No está en la lista.")

    elif command == "/blocklist":
        if SETTINGS["blocked_words"]:
            words = "\n".join(
                [f"• `{w}`" for w in SETTINGS["blocked_words"]]
            )
            await event.respond(
                f"🚫 **Bloqueadas:**\n\n{words}"
            )
        else:
            await event.respond("✅ Ninguna bloqueada.")

    elif command == "/channels":
        await event.respond(
            "📡 **Canales:**\n\n"
            f"**Fuente:** Switzy VIP Gold\n"
            f"**Fuente ID:** `{SOURCE_CHANNEL}`\n\n"
            f"**Destino:** BREY TRADING FX VIP\n"
            f"**Destino ID:** `{DESTINATION_CHANNEL}`"
        )


# -------------------------------------------------------------------
# BUTTON HANDLER
# -------------------------------------------------------------------
@bot_client.on(events.CallbackQuery())
async def button_handler(event):
    if not is_authorized(event.sender_id):
        await event.answer("❌ No autorizado", alert=True)
        return

    data = event.data.decode('utf-8')

    if data == "toggle_translate":
        SETTINGS["ai_translate"] = not SETTINGS["ai_translate"]
        status = (
            "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        )
        await event.answer(f"Traducción: {status}")
        await safe_edit(
            event,
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "change_language":
        await safe_edit(
            event,
            "🌐 **Selecciona el idioma:**",
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
        await event.answer(f"✅ {lang_name}")
        await safe_edit(
            event,
            f"✅ **Idioma: {lang_name}**",
            buttons=get_language_buttons()
        )

    elif data == "toggle_pause":
        SETTINGS["paused"] = not SETTINGS["paused"]
        status = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        await event.answer(f"Bot: {status}")
        await safe_edit(
            event,
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "show_status":
        paused = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        translate = (
            "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        )
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.answer("Estado!")
        await safe_edit(
            event,
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `{translate}`\n"
            f"• Idioma: `{lang_name}`\n"
            f"• Fuente: `{SOURCE_CHANNEL}`\n"
            f"• Destino: `{DESTINATION_CHANNEL}`\n\n"
            f"✅ Bot funcionando correctamente",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "show_channels":
        await event.answer("Canales!")
        await safe_edit(
            event,
            f"📡 **Canales:**\n\n"
            f"• **Fuente:** Switzy VIP Gold\n"
            f"• **ID:** `{SOURCE_CHANNEL}`\n\n"
            f"• **Destino:** BREY TRADING FX VIP\n"
            f"• **ID:** `{DESTINATION_CHANNEL}`",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "back_menu":
        await safe_edit(
            event,
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "close":
        await event.delete()


# -------------------------------------------------------------------
# ALBUM HANDLER
# -------------------------------------------------------------------
@user_client.on(events.Album(chats=[SOURCE_CHANNEL]))
async def album_handler(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    for msg in event.messages:
        if is_noforwards(msg):
            print("⏭️ Skipped album: noforwards")
            return

    for msg in event.messages:
        if is_audio_message(msg) or is_video_message(msg):
            print("⏭️ Skipped album: audio/video")
            return

    caption = None
    for msg in event.messages:
        if msg.message:
            raw = msg.message
            if is_promotional(raw):
                print("⏭️ Skipped album: promotional")
                return
            if is_blocked_word_found(raw):
                print("⏭️ Skipped album: blocked word")
                return
            caption = process_message(raw)
            break

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
@user_client.on(events.NewMessage(chats=[SOURCE_CHANNEL]))
async def replication_engine(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    if event.message.grouped_id:
        return

    if is_noforwards(event.message):
        print("⏭️ Skipped: noforwards")
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

    if raw_text and is_promotional(raw_text):
        print("⏭️ Skipped: promotional")
        return

    if raw_text and is_blocked_word_found(raw_text):
        print("⏭️ Skipped: blocked word")
        return

    if not has_media and raw_text:
        if not is_valid_signal(raw_text):
            print("⏭️ Skipped: not a valid signal")
            return

    final_text = process_message(raw_text) if raw_text else None

    if raw_text and not final_text:
        print("⏭️ Skipped: text empty after cleaning")
        return

    try:
        if is_photo:
            await user_client.send_file(
                destination_id,
                event.message.media,
                caption=final_text
            )
        elif has_media and not is_photo:
            if not raw_text:
                print("⏭️ Skipped: non-photo no text")
                return
            await user_client.send_message(
                destination_id, final_text
            )
        else:
            if not final_text:
                return
            await user_client.send_message(
                destination_id, final_text
            )
        print(f"✅ Signal: {source_id} → {destination_id}")
    except Exception as e:
        print(f"❌ Delivery failed: {e}")


# -------------------------------------------------------------------
# MAIN — with auto-reconnect
# -------------------------------------------------------------------
async def main():
    # Connect userbot
    await user_client.connect()

    # Validate session
    try:
        if not await user_client.is_user_authorized():
            print("❌ ERROR: Session string invalid or expired!")
            print("Please generate a new session string.")
            return
    except (
        SessionExpiredError,
        SessionRevokedError,
        AuthKeyUnregisteredError
    ) as e:
        print(f"❌ Session error: {e}")
        print("Please generate a new session string.")
        return

    print("✅ Userbot connected and authorized.")
    print(f"📡 Monitoring source: {SOURCE_CHANNEL}")

    # Start bot
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("📋 Signals copied exactly — no translation")
    print("🚫 Error texts: REMOVED from messages")
    print("🚫 Promotional messages: BLOCKED")
    print(f"📡 {SOURCE_CHANNEL} → {DESTINATION_CHANNEL}\n")

    # Keep both clients alive with auto-reconnect
    while True:
        try:
            await asyncio.gather(
                user_client.run_until_disconnected(),
                bot_client.run_until_disconnected()
            )
            break
        except (
            SessionExpiredError,
            SessionRevokedError,
            AuthKeyUnregisteredError
        ) as e:
            print(f"❌ Fatal session error: {e}")
            print("Session expired — please regenerate.")
            break
        except Exception as e:
            print(f"⚠️ Connection dropped: {e}")
            print("🔄 Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            try:
                await user_client.connect()
                await bot_client.connect()
                print("✅ Reconnected successfully.")
            except Exception as re:
                print(f"❌ Reconnect failed: {re}")
                await asyncio.sleep(10)


asyncio.run(main())
