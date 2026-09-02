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
from deep_translator.exceptions import NotValidPayload, TranslationNotFound

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
# Bot output must always be in Spanish. These act as a fast
# safety-net pass AFTER the AI translation step below, in case
# the translator leaves a term untranslated or phrases it oddly.
WORD_REPLACEMENTS = {
    r"\bSELL\b": "VENDER",
    r"\bBUY\b": "COMPRAR",
    r"\bSell\b": "Vender",
    r"\bBuy\b": "Comprar",
    r"\bsell\b": "vender",
    r"\bbuy\b": "comprar",
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
# Language is locked to Spanish per client requirement — no toggle,
# no per-message override. Output translation now runs through
# deep-translator (Google Translate) for anything the regex rules
# don't anticipate, with the regex rules applied afterward as a
# safety net / normalizer for trading-specific terms.
SETTINGS = {
    "ai_translate": True,
    "target_language": "es",
    "paused": False,
    "custom_replacements": {},
    "blocked_words": [],
}

print("Starting Brey Trading Signal Bot...")

user_client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH
)
bot_client = TelegramClient(StringSession(), API_ID, API_HASH)

# Reused across calls; deep_translator instances are lightweight.
_translator = GoogleTranslator(source="auto", target="es")

# Tokens we never want handed to the translator, since it can
# mangle tickers/prices/emojis or "translate" things that should
# stay literal. These are pulled out before translation and
# stitched back in afterward.
_PROTECT_PATTERNS = [
    r"XAU/?USD",
    r"\bTP\s*\d\b",
    r"\bSL\b",
    r"@\w+",
    r"https?://\S+",
    r"\d{1,3}(?:[.,]\d+)?",
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
    """Strip error messages from source channel posts."""
    if not text:
        return text
    for pattern in ERROR_TEXTS_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _has_letters(s):
    return bool(re.search(r"[A-Za-zÀ-ÿ]", s))


def translate_line_to_spanish(line):
    """Translate a single line to Spanish via deep-translator,
    protecting tickers/prices/handles/links from being touched.
    Falls back to the original line on any failure so a network
    hiccup never blocks message delivery."""
    stripped = line.strip()
    if not stripped or not _has_letters(stripped):
        return line

    # Pull out tokens that must not be translated, replace with
    # placeholders, translate, then restore them.
    protected = []

    def _stash(match):
        protected.append(match.group(0))
        return f"§{len(protected) - 1}§"

    placeholder_text = _PROTECT_RE.sub(_stash, stripped)

    try:
        translated = _translator.translate(placeholder_text)
        if not translated:
            return line
    except (NotValidPayload, TranslationNotFound):
        return line
    except Exception as e:
        print(f"⚠️ Translation failed for line, keeping original: {e}")
        return line

    # Restore protected tokens back into the translated text.
    def _restore(match):
        idx = int(match.group(1))
        return protected[idx] if idx < len(protected) else match.group(0)

    translated = re.sub(r"§(\d+)§", _restore, translated)

    # Preserve original leading/trailing whitespace of the line.
    leading = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]
    return f"{leading}{translated}{trailing}"


def translate_to_spanish(text):
    """Translate any remaining English (or other language) content
    to Spanish, line by line, so message structure/line breaks are
    preserved. Runs before the regex trading-term safety net."""
    if not text:
        return text
    if not SETTINGS.get("ai_translate", True):
        return text
    lines = text.split('\n')
    translated_lines = [translate_line_to_spanish(line) for line in lines]
    return '\n'.join(translated_lines)


def clean_message(text):
    """Remove names, links, errors. Translate to Spanish, then
    force-fix trading jargon via regex as a safety net."""
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

    # --- AI TRANSLATION PASS ---
    # Catches any English phrasing the regex rules below don't
    # anticipate (new slang, emphasis like "Let's FUCKN GOO",
    # unusual sentence structure, casual commentary, etc.)
    text = translate_to_spanish(text)

    # --- REGEX SAFETY NET ---
    # Normalizes trading-specific terms/formatting after
    # translation, in case the translator phrases them oddly.
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
    # Common English trading phrases -> Spanish, so nothing
    # slips through to the destination channel in English, even
    # if the translation pass above missed something.
    # Multi-word phrases first to avoid partial-match conflicts.
    text = re.sub(r'\btrail\s+sl\s+to\s+maximize\s+profits?\b', 'Mover SL para maximizar ganancias', text, flags=re.IGNORECASE)
    text = re.sub(r'\btrail\s+sl\b', 'Mover SL', text, flags=re.IGNORECASE)
    text = re.sub(r'\bto\s+maximize\s+profits?\b', 'para maximizar ganancias', text, flags=re.IGNORECASE)
    text = re.sub(r'\bfirst\s+entry\b', 'primera entrada', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsecond\s+entry\b', 'segunda entrada', text, flags=re.IGNORECASE)
    text = re.sub(r'\bthird\s+entry\b', 'tercera entrada', text, flags=re.IGNORECASE)
    text = re.sub(r'\bclose\s+position\b', 'cerrar posición', text, flags=re.IGNORECASE)
    text = re.sub(r'\bclose\b', 'cerrar', text, flags=re.IGNORECASE)
    text = re.sub(r'\bbreak\s+even\b', 'punto de equilibrio', text, flags=re.IGNORECASE)
    text = re.sub(r'\bbreakeven\b', 'punto de equilibrio', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsignal\s+ready\b', 'señal lista', text, flags=re.IGNORECASE)
    text = re.sub(r'\btake\s*profit\b', 'tomar ganancias', text, flags=re.IGNORECASE)
    text = re.sub(r'\bstop\s*loss\b', 'stop loss', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmaximize\s+profits?\b', 'maximizar ganancias', text, flags=re.IGNORECASE)
    text = re.sub(r'\bentry\b', 'entrada', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsecure\b', 'asegurar', text, flags=re.IGNORECASE)
    text = re.sub(r"\bthat'?s\b", 'eso son', text, flags=re.IGNORECASE)
    text = re.sub(r'\bbanked\b', 'aseguradas', text, flags=re.IGNORECASE)
    text = re.sub(r'\bhits\b', 'alcanzado', text, flags=re.IGNORECASE)
    text = re.sub(r'\bmove\b', 'mover', text, flags=re.IGNORECASE)
    text = re.sub(r'\bposition\b', 'posición', text, flags=re.IGNORECASE)
    text = re.sub(r'\bon\b', 'en', text, flags=re.IGNORECASE)
    # Ordinal signal labels → Spanish (after multi-word phrases above)
    text = re.sub(r'\bFIRST\b', 'PRIMERA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bSECOND\b', 'SEGUNDA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bTHIRD\b', 'TERCERA', text, flags=re.IGNORECASE)
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
    """Clean → remove errors → translate/force Spanish terms → sign."""
    if not raw_text:
        return None
    text = clean_message(raw_text)
    if not text:
        return None
    return text + SIGNATURE


# -------------------------------------------------------------------
# MENU HELPERS
# -------------------------------------------------------------------
def get_main_menu_buttons():
    pause_label = (
        "▶️ Resume" if SETTINGS["paused"] else "⏸ Pause"
    )
    return [
        [Button.inline("🇪🇸 Idioma: Español (fijo)", "noop")],
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
            "🇪🇸 Idioma de salida: **Español (fijo)**\n"
            "🤖 Traducción: **Automática (Google Translate)**\n"
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
            "➡️ `/addword vieja:nueva` - Reemplazar\n"
            "➡️ `/removeword palabra` - Quitar\n"
            "➡️ `/wordlist` - Ver reemplazos\n"
            "➡️ `/blockword palabra` - Bloquear\n"
            "➡️ `/unblockword palabra` - Desbloquear\n"
            "➡️ `/blocklist` - Ver bloqueadas\n"
            "➡️ `/channels` - Ver canales\n"
            "➡️ `/ping` - Verificar bot activo\n\n"
            "🇪🇸 Nota: el idioma de salida está fijo en Español,\n"
            "traducido automáticamente con respaldo de reglas\n"
            "para términos de trading."
        )

    elif command == "/status":
        paused = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        await event.respond(
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Idioma: `Español (fijo)`\n"
            f"• Traducción automática: `{'ON' if SETTINGS['ai_translate'] else 'OFF'}`\n"
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

    if data == "noop":
        await event.answer("El idioma está fijo en Español.")

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
        await event.answer("Estado!")
        await safe_edit(
            event,
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Idioma: `Español (fijo)`\n"
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
            f"• **ID Fuente:** `{SOURCE_CHANNEL}`\n\n"
            f"• **Destino:** BREY TRADING FX VIP\n"
            f"• **ID Destino:** `{DESTINATION_CHANNEL}`",
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
# MAIN — with resilient, independent auto-reconnect for both clients
# -------------------------------------------------------------------
async def run_client_forever(client, name, start_kwargs=None):
    """Keep a single client connected indefinitely. Runs its own
    retry loop so a drop in one client never blocks or delays the
    other — signals keep flowing the instant the source posts."""
    backoff = 5
    while True:
        try:
            if not client.is_connected():
                await client.connect()

            if start_kwargs is not None:
                await client.start(**start_kwargs)
            else:
                if not await client.is_user_authorized():
                    print(f"❌ ERROR: {name} session invalid/expired!")
                    print("Please generate a new session string.")
                    return

            print(f"✅ {name} connected.")
            backoff = 5  # reset backoff after a clean connect
            await client.run_until_disconnected()
            print(f"⚠️ {name} disconnected. Reconnecting immediately...")

        except (
            SessionExpiredError,
            SessionRevokedError,
            AuthKeyUnregisteredError,
        ) as e:
            print(f"❌ Fatal session error on {name}: {e}")
            print("Session expired — please regenerate.")
            return
        except Exception as e:
            print(f"⚠️ {name} connection error: {e}")
            print(f"🔄 Retrying {name} in {backoff} seconds...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


async def main():
    await user_client.connect()
    try:
        if not await user_client.is_user_authorized():
            print("❌ ERROR: Session string invalid or expired!")
            print("Please generate a new session string.")
            return
    except (
        SessionExpiredError,
        SessionRevokedError,
        AuthKeyUnregisteredError,
    ) as e:
        print(f"❌ Session error: {e}")
        print("Please generate a new session string.")
        return

    print("✅ Userbot connected and authorized.")
    print(f"📡 Monitoring source: {SOURCE_CHANNEL}")

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("📋 Signals copied — output forced to Spanish")
    print("🤖 Auto-translation: Google Translate + regex safety net")
    print("🚫 Error texts: REMOVED from messages")
    print("🚫 Promotional messages: BLOCKED")
    print(f"📡 {SOURCE_CHANNEL} → {DESTINATION_CHANNEL}\n")

    # Each client gets its own independent forever-loop so a
    # reconnect on one never stalls delivery on the other — the
    # bot effectively never rests.
    await asyncio.gather(
        run_client_forever(user_client, "Userbot"),
        run_client_forever(
            bot_client, "Bot", start_kwargs={"bot_token": BOT_TOKEN}
        ),
    )


asyncio.run(main())

