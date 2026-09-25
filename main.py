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
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    NotValidPayload,
    TranslationNotFound,
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
    r"Alpha\s*Gold\s*-\s*Switzy\s*",
    r"Alpha\s*Gold\s*Switzy\s*",
    r"Switzy\s*VIP\s*Gold\s*",
    r"Switzy\s*Personal\s*",
    r"Switzy\s*",
    r"@\w+",
    r"t\.me/\S+",
    r"https?://\S+",
    r"www\.\S+",
]

# --- SIGNATURE ---
SIGNATURE = "\n\n📊 Brey's Signals | @BREYTRADING"

# --- ERROR TEXTS TO STRIP ---
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
    r"\btp\b",
    r"take profit",
    r"\bsl\b",
    r"sl\s*hit",
    r"stop loss",
    r"entrar entre",
    r"\bentry\b",
    r"\bentrada\b",
    r"first entry",
    r"second entry",
    r"primera entrada",
    r"segunda entrada",
    r"break even",
    r"breakeven",
    r"break en",
    r"colocar break",
    r"coloquen break",
    r"place break",
    r"move sl",
    r"trail sl",
    r"mover sl",
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
    r"close first",
    r"onto next",
    r"next opportunity",
    r"maximize profit",
    r"maximizar ganancias",
    r"50%",
    r"\+\d+\s*pips",
    r"sl\s*golpe",
    r"gol de sl",
    r"punto de equilibrio",
]

# --- SYSTEM VARIABLES ---
SETTINGS = {
    "ai_translate": True,
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

_translator = GoogleTranslator(source="auto", target="es")

_PROTECT_PATTERNS = [
    r"XAU/?USD",
    r"\bTP\s*\d\b",
    r"\bSL\b",
    r"\d{3,5}(?:\.\d+)?",
]
_PROTECT_RE = re.compile(
    "|".join(_PROTECT_PATTERNS), flags=re.IGNORECASE
)


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
    if not text:
        return text
    for pattern in ERROR_TEXTS_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _has_letters(s):
    return bool(re.search(r"[A-Za-zÀ-ÿ]", s))


def translate_line(line):
    """Translate one line, protecting tickers and numbers."""
    stripped = line.strip()
    if not stripped or not _has_letters(stripped):
        return line

    protected = []

    def _stash(match):
        protected.append(match.group(0))
        return f"§{len(protected) - 1}§"

    placeholder = _PROTECT_RE.sub(_stash, stripped)

    try:
        translated = _translator.translate(placeholder)
        if not translated:
            return line
    except (NotValidPayload, TranslationNotFound):
        return line
    except Exception as e:
        print(f"⚠️ Line translation failed: {e}")
        return line

    def _restore(match):
        idx = int(match.group(1))
        return (
            protected[idx]
            if idx < len(protected)
            else match.group(0)
        )

    translated = re.sub(r"§(\d+)§", _restore, translated)
    leading = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]
    return f"{leading}{translated}{trailing}"


def translate_to_spanish(text):
    if not text or not SETTINGS.get("ai_translate", True):
        return text
    lines = text.split('\n')
    return '\n'.join(translate_line(l) for l in lines)


def clean_message(text):
    """Remove names/errors → translate → normalize."""
    if not text:
        return text

    # Remove error texts
    text = remove_error_texts(text)

    # Remove source channel names
    for pattern in NAMES_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove links
    text = re.sub(
        r'https?://\S+|t\.me/\S+|www\.\S+|joinchat/\S+',
        '', text
    )

    # Remove @handles
    text = re.sub(r'@\w+', '', text)

    # Custom replacements
    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(
            re.escape(old), new, text, flags=re.IGNORECASE
        )

    # Translate to Spanish
    text = translate_to_spanish(text)

    # Normalize trading terms after translation
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

    # English → Spanish trading phrases
    phrase_map = [
        (r'\btrail\s+sl\s+to\s+maximize\s+profits?\b',
         'Mover SL para maximizar ganancias'),
        (r'\btrail\s+sl\b', 'Mover SL'),
        (r'\bfirst\s+entry\b', 'primera entrada'),
        (r'\bsecond\s+entry\b', 'segunda entrada'),
        (r'\bclose\s+first\s+position\b', 'cerrar primera posición'),
        (r'\bclose\s+position\b', 'cerrar posición'),
        (r'\bbreak\s+even\b', 'punto de equilibrio'),
        (r'\bbreakeven\b', 'punto de equilibrio'),
        (r'\bsl\s+hit\b', 'SL alcanzado'),
        (r'\bonto\s+next\s+opportunity\b',
         'a la siguiente oportunidad'),
        (r'\bnext\s+opportunity\b', 'siguiente oportunidad'),
        (r'\bmove\s+sl\b', 'mover SL'),
        (r'\bsignal\s+ready\b', 'señal lista'),
        (r'\btake\s*profit\b', 'tomar ganancias'),
        (r'\bstop\s*loss\b', 'stop loss'),
        (r'\bmaximize\s+profits?\b', 'maximizar ganancias'),
        (r'\bentry\b', 'entrada'),
        (r'\bsecure\b', 'asegurar'),
        (r'\bsl\s+golpe\b', 'SL alcanzado'),
        (r'\bFIRST\b', 'PRIMERA'),
        (r'\bSECOND\b', 'SEGUNDA'),
        (r'\bSELL\b', 'VENDER'),
        (r'\bBUY\b', 'COMPRAR'),
    ]
    for pattern, replacement in phrase_map:
        text = re.sub(
            pattern, replacement, text, flags=re.IGNORECASE
        )

    # Clean blank lines
    lines = text.split('\n')
    cleaned = [
        l for l in lines
        if l.strip() and not re.match(
            r'^[\s\-_•|/\\:.]+$', l.strip()
        )
    ]
    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def process_message(raw_text):
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
        current = (
            "✅ " if lang_code == SETTINGS["target_language"]
            else ""
        )
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
            "👋 Bienvenido a Brey Trading Signal Bot!\n\n"
            "📡 Copiando señales de Gold automáticamente\n"
            "➡️ Destino: BREY TRADING FX VIP\n\n"
            "🇪🇸 Idioma: Español\n"
            "🤖 Traducción: Automática\n"
            "🚫 Spam y errores: Bloqueados\n\n"
            "Usa los botones para controlar el bot.",
            buttons=get_main_menu_buttons()
        )

    elif command == "/menu":
        await event.respond(
            "🎛 Panel de Control:",
            buttons=get_main_menu_buttons()
        )

    elif command == "/help":
        await event.respond(
            "📋 Comandos:\n\n"
            "➡️ /start - Bienvenida\n"
            "➡️ /menu - Panel de control\n"
            "➡️ /status - Estado actual\n"
            "➡️ /ping - Verificar bot activo\n"
            "➡️ /pause - Pausar bot\n"
            "➡️ /resume - Reanudar bot\n"
            "➡️ /ai on - Activar traducción\n"
            "➡️ /ai off - Desactivar traducción\n"
            "➡️ /language es - Español\n"
            "➡️ /language en - Inglés\n"
            "➡️ /addword vieja:nueva - Reemplazar\n"
            "➡️ /removeword palabra - Quitar\n"
            "➡️ /wordlist - Ver reemplazos\n"
            "➡️ /blockword palabra - Bloquear\n"
            "➡️ /unblockword palabra - Desbloquear\n"
            "➡️ /blocklist - Ver bloqueadas\n"
            "➡️ /channels - Ver canales\n"
        )

    elif command == "/ping":
        await event.respond(
            "🏓 Pong!\n"
            "✅ Bot activo y funcionando.\n"
            f"📡 Monitoreando: {SOURCE_CHANNEL}"
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
            f"📊 Estado:\n\n"
            f"• Estado: {paused}\n"
            f"• Traducción: {translate}\n"
            f"• Idioma: {lang_name}\n"
            f"• Canal fuente: {SOURCE_CHANNEL}\n"
            f"• Canal destino: {DESTINATION_CHANNEL}\n"
            f"• Reemplazos: "
            f"{len(SETTINGS['custom_replacements'])}\n"
            f"• Palabras bloqueadas: "
            f"{len(SETTINGS['blocked_words'])}\n\n"
            f"✅ Bot funcionando correctamente"
        )

    elif command == "/pause":
        SETTINGS["paused"] = True
        await event.respond("⏸ Bot Pausado.")

    elif command == "/resume":
        SETTINGS["paused"] = False
        await event.respond(
            "▶️ Bot Reanudado.\n"
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
            f"✅ Traducción ACTIVADA → {lang_name}"
        )

    elif command == "/ai off":
        SETTINGS["ai_translate"] = False
        await event.respond("🛑 Traducción DESACTIVADA.")

    elif command.startswith("/language "):
        lang = command.split("/language ")[1].strip()
        if lang in LANGUAGES.values():
            SETTINGS["target_language"] = lang
            # Update translator target
            global _translator
            _translator = GoogleTranslator(
                source="auto", target=lang
            )
            lang_name = next(
                (k for k, v in LANGUAGES.items()
                 if v == lang), lang
            )
            await event.respond(
                f"🌐 Idioma: {lang_name}"
            )
        else:
            await event.respond(
                f"❌ No soportado: {lang}\n"
                f"Opciones: en, es, fr, de, pt, ar, zh, ru, it"
            )

    elif full_text.lower().startswith("/addword "):
        try:
            parts = full_text[9:].split(":")
            if len(parts) == 2:
                old_word = parts[0].strip()
                new_word = parts[1].strip()
                SETTINGS["custom_replacements"][old_word] = (
                    new_word
                )
                await event.respond(
                    f"✅ {old_word} → {new_word}"
                )
            else:
                await event.respond(
                    "❌ Usa: /addword palabravieja:nuevapalabra"
                )
        except Exception:
            await event.respond(
                "❌ Usa: /addword palabravieja:nuevapalabra"
            )

    elif full_text.lower().startswith("/removeword "):
        word = full_text[12:].strip()
        if word in SETTINGS["custom_replacements"]:
            del SETTINGS["custom_replacements"][word]
            await event.respond(f"✅ Eliminado: {word}")
        else:
            await event.respond(f"❌ {word} no encontrado.")

    elif command == "/wordlist":
        if SETTINGS["custom_replacements"]:
            replacements = "\n".join(
                [f"• {k} → {v}"
                 for k, v in SETTINGS[
                     "custom_replacements"
                 ].items()]
            )
            await event.respond(
                f"📝 Reemplazos:\n\n{replacements}"
            )
        else:
            await event.respond(
                "📝 Ninguno. Usa /addword vieja:nueva"
            )

    elif full_text.lower().startswith("/blockword "):
        word = full_text[11:].strip()
        if word not in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].append(word)
            await event.respond(f"🚫 Bloqueado: {word}")
        else:
            await event.respond(f"⚠️ Ya bloqueado.")

    elif full_text.lower().startswith("/unblockword "):
        word = full_text[13:].strip()
        if word in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].remove(word)
            await event.respond(f"✅ Desbloqueado: {word}")
        else:
            await event.respond(f"❌ No está en la lista.")

    elif command == "/blocklist":
        if SETTINGS["blocked_words"]:
            words = "\n".join(
                [f"• {w}" for w in SETTINGS["blocked_words"]]
            )
            await event.respond(
                f"🚫 Bloqueadas:\n\n{words}"
            )
        else:
            await event.respond("✅ Ninguna bloqueada.")

    elif command == "/channels":
        await event.respond(
            "📡 Canales:\n\n"
            f"Fuente ID: {SOURCE_CHANNEL}\n\n"
            f"Destino: BREY TRADING FX VIP\n"
            f"Destino ID: {DESTINATION_CHANNEL}"
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
            "🎛 Panel de Control:",
            buttons=get_main_menu_buttons()
        )

    elif data == "change_language":
        await safe_edit(
            event,
            "🌐 Selecciona el idioma:",
            buttons=get_language_buttons()
        )

    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        SETTINGS["target_language"] = lang_code
        global _translator
        _translator = GoogleTranslator(
            source="auto", target=lang_code
        )
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == lang_code),
            lang_code
        )
        await event.answer(f"✅ {lang_name}")
        await safe_edit(
            event,
            f"✅ Idioma: {lang_name}",
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
            "🎛 Panel de Control:",
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
            f"📊 Estado:\n\n"
            f"• Estado: {paused}\n"
            f"• Traducción: {translate}\n"
            f"• Idioma: {lang_name}\n"
            f"• Fuente: {SOURCE_CHANNEL}\n"
            f"• Destino: {DESTINATION_CHANNEL}\n\n"
            f"✅ Bot funcionando correctamente",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "show_channels":
        await event.answer("Canales!")
        await safe_edit(
            event,
            f"📡 Canales:\n\n"
            f"• Fuente ID: {SOURCE_CHANNEL}\n\n"
            f"• Destino: BREY TRADING FX VIP\n"
            f"• Destino ID: {DESTINATION_CHANNEL}",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "back_menu":
        await safe_edit(
            event,
            "🎛 Panel de Control:",
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
            print(
                f"⏭️ Skipped: not valid signal: "
                f"{raw_text[:40]}"
            )
            return

    final_text = (
        process_message(raw_text) if raw_text else None
    )

    if raw_text and not final_text:
        print("⏭️ Skipped: empty after cleaning")
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
# RESILIENT CLIENT RUNNER
# -------------------------------------------------------------------
async def run_client_forever(client, name, start_kwargs=None):
    backoff = 5
    while True:
        try:
            if not client.is_connected():
                await client.connect()

            if start_kwargs is not None:
                await client.start(**start_kwargs)
            else:
                if not await client.is_user_authorized():
                    print(
                        f"❌ {name} session invalid/expired!\n"
                        "Please regenerate the session string."
                    )
                    return

            print(f"✅ {name} connected.")
            backoff = 5
            await client.run_until_disconnected()
            print(
                f"⚠️ {name} disconnected. Reconnecting..."
            )

        except (
            SessionExpiredError,
            SessionRevokedError,
            AuthKeyUnregisteredError,
        ) as e:
            print(f"❌ Fatal session error on {name}: {e}")
            return
        except Exception as e:
            print(f"⚠️ {name} error: {e}")
            print(f"🔄 Retrying {name} in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
async def main():
    await user_client.connect()

    try:
        if not await user_client.is_user_authorized():
            print("❌ Session string invalid or expired!")
            print("Please regenerate the session string.")
            return
    except (
        SessionExpiredError,
        SessionRevokedError,
        AuthKeyUnregisteredError,
    ) as e:
        print(f"❌ Session error: {e}")
        return

    print("✅ Userbot connected and authorized.")
    print(f"📡 Source: {SOURCE_CHANNEL}")

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("🇪🇸 Output: Spanish")
    print("🤖 Translation: Google Translate + safety net")
    print("🚫 Error texts: REMOVED")
    print("🚫 Promotional: BLOCKED")
    print("🔄 Auto-reconnect: ENABLED")
    print(f"📡 {SOURCE_CHANNEL} → {DESTINATION_CHANNEL}\n")

    await asyncio.gather(
        run_client_forever(user_client, "Userbot"),
        run_client_forever(
            bot_client, "Bot",
            start_kwargs={"bot_token": BOT_TOKEN}
        ),
    )


asyncio.run(main())
