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
    FloodWaitError,
    ChatWriteForbiddenError,
    ChannelPrivateError,
    MessageNotModifiedError,
    SlowModeWaitError,
    ServerError,
    RpcCallFailError,
    BadRequestError,
)
from deep_translator import GoogleTranslator

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

# --- TRADING TERMS TO PRESERVE (never translate these) ---
PRESERVE_TERMS = {
    "XAUUSD": "__XAUUSD__",
    "XAU/USD": "__XAUUSD2__",
    "XAU": "__XAU__",
    "TP1": "__TP1__",
    "TP2": "__TP2__",
    "TP3": "__TP3__",
    "TP4": "__TP4__",
    "TP5": "__TP5__",
    "SL": "__SL__",
    "BUY": "__BUY__",
    "SELL": "__SELL__",
    "SCALP": "__SCALP__",
    "SCALPING": "__SCALPING__",
    "BREAKEVEN": "__BREAKEVEN__",
    "BREAK EVEN": "__BREAKEVEN2__",
    "PIPS": "__PIPS__",
    "PIP": "__PIP__",
}

RESTORE_TERMS = {v: k for k, v in PRESERVE_TERMS.items()}

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

# --- SIGNATURE ---
SIGNATURE = "\n\n📊 Brey's Signals | @BREYTRADING"

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
    r"interacción",
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
    # --- ALL ERROR MESSAGE PATTERNS BLOCKED UPFRONT ---
    r"error\s*5\d\d",
    r"server\s*error",
    r"there was an error",
    r"please try again",
    r"try again later",
    r"that'?s all we know",
    r"thats all we know",
    r"error.*servidor",
    r"intenta.*más tarde",
    r"!!1500",
    r"1500\.that",
    r"1500\.",
    r"\b1500\b",
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
    r"50%",
]

# --- SYSTEM VARIABLES ---
SETTINGS = {
    "paused": False,
    "custom_replacements": {},
    "blocked_words": [],
}

# --- SEND QUEUE (prevents rapid-fire sends that cause rate limits) ---
_send_queue = asyncio.Queue()
_send_lock = asyncio.Lock()

print("Starting Brey Trading Signal Bot...")

user_client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH
)
bot_client = TelegramClient(StringSession(), API_ID, API_HASH)


# ===================================================================
# ERROR TEXT DETECTION — runs BEFORE any processing
# ===================================================================

# Compiled once at startup for performance
_ERROR_RAW_PATTERNS = re.compile(
    r"(Error\s*5\d\d"
    r"|Server\s*Error"
    r"|There\s+was\s+an\s+error"
    r"|Please\s+try\s+again"
    r"|try\s+again\s+later"
    r"|That'?s\s+all\s+we\s+know"
    r"|!!1500"
    r"|1500\.?"
    r"|\b500\b.*error"
    r"|RpcCallFail"
    r"|Internal\s+Server)",
    re.IGNORECASE,
)

_ERROR_LINE_PATTERNS = re.compile(
    r"(error\s*5\d\d"
    r"|server\s*error"
    r"|there\s+was\s+an\s+error"
    r"|please\s+try\s+again"
    r"|try\s+again\s+later"
    r"|that'?s\s+all\s+we\s+know"
    r"|!!1500"
    r"|\b1500\b"
    r"|an\s+error\.)",
    re.IGNORECASE,
)

_ERROR_INLINE_PATTERNS = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in [
        r"Error\s*5\d\d\s*\(Server Error\)[^.]*?That'?s all we know\.?",
        r"Error\s*5\d\d\s*\(Server Error\)[^\n]*",
        r"!!1500\.?That'?s an error\.",
        r"There was an error\.\s*Please try again later\.",
        r"Please try again later\.?\s*That'?s all we know\.?",
        r"That'?s all we know\.?",
        r"There was an error\.",
        r"Please try again later\.",
        r"!!1500",
        r"\b1500\b",
    ]
]


def is_pure_error_message(text: str) -> bool:
    """
    Returns True if the ENTIRE message is an error message
    (no real signal content). Checked BEFORE any processing.
    """
    if not text:
        return False
    return bool(_ERROR_RAW_PATTERNS.search(text))


def strip_error_fragments(text: str) -> str:
    """
    Surgically removes error text fragments embedded inside
    an otherwise valid signal. Runs inline AND line-by-line.
    """
    if not text:
        return text

    # Pass 1: remove inline error blocks (multi-word patterns first)
    for pattern in _ERROR_INLINE_PATTERNS:
        text = pattern.sub("", text)

    # Pass 2: remove full lines that are pure error lines
    lines = text.split("\n")
    clean = []
    for line in lines:
        if _ERROR_LINE_PATTERNS.search(line):
            print(f"🧹 Stripped error line: {line.strip()!r}")
        else:
            clean.append(line)

    text = "\n".join(clean)

    # Pass 3: collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ===================================================================
# TRANSLATION
# ===================================================================

def protect_terms(text: str) -> str:
    for term, placeholder in PRESERVE_TERMS.items():
        text = re.compile(re.escape(term), re.IGNORECASE).sub(
            placeholder, text
        )
    return text


def restore_terms(text: str) -> str:
    for placeholder, term in RESTORE_TERMS.items():
        text = text.replace(placeholder, term)
    return text


def translate_to_spanish(text: str) -> str:
    if not text or not text.strip():
        return text
    try:
        protected = protect_terms(text)
        lines = protected.split("\n")
        translated_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                translated_lines.append("")
                continue

            if re.match(r"^[\d\s.\-+:%__]+$", stripped):
                translated_lines.append(line)
                continue

            if all(
                w.startswith("__") and w.endswith("__")
                for w in stripped.split()
                if w
            ):
                translated_lines.append(line)
                continue

            try:
                translated = GoogleTranslator(
                    source="auto", target="es"
                ).translate(stripped)
                translated_lines.append(
                    translated if translated else stripped
                )
            except Exception:
                translated_lines.append(line)

        result = "\n".join(translated_lines)
        result = restore_terms(result)

        # Normalise key terms
        result = re.sub(r"\bxauusd\b", "XAUUSD", result, flags=re.IGNORECASE)
        result = re.sub(r"\bxau/usd\b", "XAU/USD", result, flags=re.IGNORECASE)
        result = re.sub(r"\btp(\d)\b", r"TP\1", result, flags=re.IGNORECASE)
        result = re.sub(r"\bsl\b", "SL", result, flags=re.IGNORECASE)

        print("✅ Translated to Spanish")
        return result

    except Exception as e:
        print(f"⚠️ Translation error: {e} — using original")
        return text


# ===================================================================
# HELPERS
# ===================================================================

def is_authorized(sender_id: int) -> bool:
    return sender_id == OWNER_ID


def is_audio_message(message) -> bool:
    if not message.media:
        return False
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if getattr(doc, "mime_type", "").startswith("audio/"):
            return True
        for attr in getattr(doc, "attributes", []):
            if type(attr).__name__ in (
                "DocumentAttributeAudio", "DocumentAttributeVoice"
            ):
                return True
    return False


def is_video_message(message) -> bool:
    if not message.media:
        return False
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if getattr(doc, "mime_type", "").startswith("video/"):
            return True
        for attr in getattr(doc, "attributes", []):
            if type(attr).__name__ == "DocumentAttributeVideo":
                return True
    return False


def is_photo_message(message) -> bool:
    return isinstance(message.media, MessageMediaPhoto)


def is_noforwards(message) -> bool:
    return getattr(message, "noforwards", False)


def is_promotional(text: str) -> bool:
    if not text:
        return False
    for pattern in BLOCKED_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"🚫 Blocked phrase: {pattern!r}")
            return True
    return False


def is_valid_signal(text: str) -> bool:
    if not text:
        return False
    return any(
        re.search(p, text, re.IGNORECASE)
        for p in GOLD_SIGNAL_PATTERNS
    )


def is_blocked_word_found(text: str) -> bool:
    if not text:
        return False
    return any(
        w.lower() in text.lower() for w in SETTINGS["blocked_words"]
    )


def clean_message(text: str) -> str:
    if not text:
        return text

    # Strip error fragments FIRST, before anything else
    text = strip_error_fragments(text)

    for pattern in NAMES_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(
        r"https?://\S+|t\.me/\S+|www\.\S+|joinchat/\S+",
        "", text,
    )
    text = re.sub(r"@\w+", "", text)

    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)

    lines = [
        ln for ln in text.split("\n")
        if ln.strip() and not re.match(r"^[\s\-_•|/\\:.]+$", ln.strip())
    ]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def apply_spanish_fixes(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\bBUY\b", "COMPRAR", text)
    text = re.sub(r"\bSELL\b", "VENDER", text)
    text = re.sub(r"\bComprar\b", "COMPRAR", text)
    text = re.sub(r"\bVender\b", "VENDER", text)
    text = re.sub(r"\bxauusd\b", "XAUUSD", text, flags=re.IGNORECASE)
    text = re.sub(r"\bxau/usd\b", "XAU/USD", text, flags=re.IGNORECASE)
    text = re.sub(r"\btp(\d)\b", r"TP\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsl\b", "SL", text, flags=re.IGNORECASE)
    return text


def process_message(raw_text: str):
    """
    Full pipeline:
      1. Detect pure error messages → reject immediately
      2. Clean watermarks + strip embedded errors
      3. Translate to Spanish
      4. Post-translation fixes
      5. Sign
    Returns None if nothing valid remains.
    """
    if not raw_text:
        return None

    # --- GATE 1: reject messages that ARE error messages ---
    if is_pure_error_message(raw_text):
        print("🚫 Rejected: pure error message")
        return None

    text = clean_message(raw_text)
    if not text:
        return None

    # --- GATE 2: after cleaning, re-check if anything valid remains ---
    if is_pure_error_message(text):
        print("🚫 Rejected: only error content after cleaning")
        return None

    text = translate_to_spanish(text)
    if not text:
        return None

    text = apply_spanish_fixes(text)
    return text + SIGNATURE


# ===================================================================
# SAFE SEND WITH RETRY + FLOOD WAIT HANDLING
# ===================================================================

async def safe_send(coro_factory, retries: int = 3, base_delay: float = 2.0):
    """
    Wraps a send coroutine with:
    - FloodWaitError: waits the required time then retries
    - ServerError / RpcCallFailError: exponential backoff retry
    - Other errors: logged, not retried
    """
    for attempt in range(retries):
        try:
            await coro_factory()
            return True

        except FloodWaitError as e:
            wait = e.seconds + 2
            print(f"⏳ FloodWait: sleeping {wait}s (attempt {attempt+1})")
            await asyncio.sleep(wait)

        except SlowModeWaitError as e:
            wait = e.seconds + 1
            print(f"⏳ SlowMode: sleeping {wait}s")
            await asyncio.sleep(wait)

        except (ServerError, RpcCallFailError) as e:
            # This is the Error 500 from Telegram's side
            delay = base_delay * (2 ** attempt)
            print(
                f"⚠️ Telegram server error (attempt {attempt+1}/{retries}): "
                f"{e} — retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except ChatWriteForbiddenError:
            print("❌ No write permission to destination channel.")
            return False

        except ChannelPrivateError:
            print("❌ Destination channel is private / bot not member.")
            return False

        except BadRequestError as e:
            print(f"❌ Bad request (not retrying): {e}")
            return False

        except Exception as e:
            delay = base_delay * (2 ** attempt)
            print(
                f"❌ Unexpected error (attempt {attempt+1}/{retries}): "
                f"{e} — retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

    print("❌ All retries exhausted — message dropped.")
    return False


# ===================================================================
# MENU HELPERS
# ===================================================================

def get_main_menu_buttons():
    pause_label = "▶️ Reanudar" if SETTINGS["paused"] else "⏸ Pausar"
    return [
        [Button.inline(pause_label, "toggle_pause")],
        [Button.inline("📊 Estado", "show_status")],
        [Button.inline("📡 Canales", "show_channels")],
        [Button.inline("❌ Cerrar", "close")],
    ]


async def safe_edit(event, text, buttons=None):
    try:
        await (event.edit(text, buttons=buttons) if buttons else event.edit(text))
    except (MessageNotModifiedError, Exception) as e:
        if "not modified" not in str(e).lower():
            print(f"Edit error: {e}")


# ===================================================================
# COMMAND HANDLER (bot_client)
# ===================================================================

@bot_client.on(events.NewMessage(pattern=r"^/"))
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
            "🌐 Traducción: **SIEMPRE ESPAÑOL** ✅\n"
            "🚫 Mensajes promocionales: **Bloqueados**\n\n"
            "Usa los botones para controlar el bot.",
            buttons=get_main_menu_buttons(),
        )

    elif command == "/menu":
        await event.respond(
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons(),
        )

    elif command == "/help":
        await event.respond(
            "📋 **Comandos:**\n\n"
            "➡️ `/start` - Bienvenida\n"
            "➡️ `/menu` - Panel de control\n"
            "➡️ `/status` - Estado actual\n"
            "➡️ `/pause` - Pausar bot\n"
            "➡️ `/resume` - Reanudar bot\n"
            "➡️ `/addword vieja:nueva` - Reemplazar palabra\n"
            "➡️ `/removeword palabra` - Quitar reemplazo\n"
            "➡️ `/wordlist` - Ver reemplazos\n"
            "➡️ `/blockword palabra` - Bloquear palabra\n"
            "➡️ `/unblockword palabra` - Desbloquear\n"
            "➡️ `/blocklist` - Ver bloqueadas\n"
            "➡️ `/channels` - Ver canales\n\n"
            "🌐 **Traducción:** Siempre Español — no configurable"
        )

    elif command == "/status":
        paused = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        await event.respond(
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `✅ SIEMPRE ESPAÑOL`\n"
            f"• Canal fuente: `{SOURCE_CHANNEL}`\n"
            f"• Canal destino: `{DESTINATION_CHANNEL}`\n"
            f"• Reemplazos: `{len(SETTINGS['custom_replacements'])}`\n"
            f"• Palabras bloqueadas: `{len(SETTINGS['blocked_words'])}`"
        )

    elif command == "/pause":
        SETTINGS["paused"] = True
        await event.respond("⏸ **Bot Pausado.**")

    elif command == "/resume":
        SETTINGS["paused"] = False
        await event.respond("▶️ **Bot Reanudado.**")

    elif full_text.lower().startswith("/addword "):
        try:
            parts = full_text[9:].split(":")
            if len(parts) == 2:
                old_word, new_word = parts[0].strip(), parts[1].strip()
                SETTINGS["custom_replacements"][old_word] = new_word
                await event.respond(f"✅ `{old_word}` → `{new_word}`")
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
                f"• `{k}` → `{v}`"
                for k, v in SETTINGS["custom_replacements"].items()
            )
            await event.respond(f"📝 **Reemplazos:**\n\n{replacements}")
        else:
            await event.respond("📝 Ninguno. Usa `/addword vieja:nueva`")

    elif full_text.lower().startswith("/blockword "):
        word = full_text[11:].strip()
        if word not in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].append(word)
            await event.respond(f"🚫 Bloqueado: `{word}`")
        else:
            await event.respond("⚠️ Ya bloqueado.")

    elif full_text.lower().startswith("/unblockword "):
        word = full_text[13:].strip()
        if word in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].remove(word)
            await event.respond(f"✅ Desbloqueado: `{word}`")
        else:
            await event.respond("❌ No está en la lista.")

    elif command == "/blocklist":
        if SETTINGS["blocked_words"]:
            words = "\n".join(f"• `{w}`" for w in SETTINGS["blocked_words"])
            await event.respond(f"🚫 **Bloqueadas:**\n\n{words}")
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


# ===================================================================
# BUTTON HANDLER (bot_client)
# ===================================================================

@bot_client.on(events.CallbackQuery())
async def button_handler(event):
    if not is_authorized(event.sender_id):
        await event.answer("❌ No autorizado", alert=True)
        return

    data = event.data.decode("utf-8")

    if data == "toggle_pause":
        SETTINGS["paused"] = not SETTINGS["paused"]
        status = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        await event.answer(f"Bot: {status}")
        await safe_edit(
            event, "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons(),
        )

    elif data == "show_status":
        paused = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        await event.answer("Estado!")
        await safe_edit(
            event,
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `✅ SIEMPRE ESPAÑOL`\n"
            f"• Fuente: `{SOURCE_CHANNEL}`\n"
            f"• Destino: `{DESTINATION_CHANNEL}`",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]],
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
            buttons=[[Button.inline("🔙 Volver", "back_menu")]],
        )

    elif data == "back_menu":
        await safe_edit(
            event, "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons(),
        )

    elif data == "close":
        await event.delete()


# ===================================================================
# ALBUM HANDLER (user_client)
# ===================================================================

@user_client.on(events.Album(chats=[SOURCE_CHANNEL]))
async def album_handler(event):
    if SETTINGS["paused"]:
        return

    destination_id = CHANNEL_MAP.get(event.chat_id)
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

            # Reject pure error messages immediately
            if is_pure_error_message(raw):
                print("⏭️ Skipped album: error message")
                return

            if is_promotional(raw):
                print("⏭️ Skipped album: promotional")
                return

            if is_blocked_word_found(raw):
                print("⏭️ Skipped album: blocked word")
                return

            caption = process_message(raw)
            if caption is None:
                print("⏭️ Skipped album: nothing valid after processing")
                return
            break

    media_files = [
        msg.media for msg in event.messages if is_photo_message(msg)
    ]

    if media_files:
        # Small delay before album sends to avoid rate-limit bursts
        await asyncio.sleep(0.5)

        async def do_send():
            await user_client.send_file(
                destination_id, media_files, caption=caption
            )

        success = await safe_send(do_send)
        if success:
            print(f"✅ Album sent → {destination_id}")
        else:
            print(f"❌ Album dropped after retries")


# ===================================================================
# SINGLE MESSAGE HANDLER (user_client)
# ===================================================================

@user_client.on(events.NewMessage(chats=[SOURCE_CHANNEL]))
async def replication_engine(event):
    if SETTINGS["paused"]:
        return

    destination_id = CHANNEL_MAP.get(event.chat_id)
    if not destination_id:
        return

    # Skip album parts (handled by album_handler)
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

    # --- GATE: reject error messages immediately, before any processing ---
    if raw_text and is_pure_error_message(raw_text):
        print("⏭️ Skipped: error message from source channel")
        return

    if raw_text and is_promotional(raw_text):
        print("⏭️ Skipped: promotional")
        return

    if raw_text and is_blocked_word_found(raw_text):
        print("⏭️ Skipped: blocked word")
        return

    # Text-only messages must be valid signals
    if not has_media and raw_text:
        if not is_valid_signal(raw_text):
            print("⏭️ Skipped: not a valid signal")
            return

    final_text = process_message(raw_text) if raw_text else None

    # After processing, if we got None (e.g. was all error text), skip
    if raw_text and final_text is None:
        print("⏭️ Skipped: nothing valid remained after processing")
        return

    # Small delay to avoid bursting the API
    await asyncio.sleep(0.3)

    if is_photo:
        async def do_send():
            await user_client.send_file(
                destination_id, event.message.media, caption=final_text
            )
    elif has_media and not is_photo:
        if not raw_text:
            print("⏭️ Skipped: non-photo no text")
            return

        async def do_send():
            await user_client.send_message(destination_id, final_text)
    else:
        if not final_text:
            return

        async def do_send():
            await user_client.send_message(destination_id, final_text)

    success = await safe_send(do_send)
    if success:
        print(f"✅ Signal (ES): {SOURCE_CHANNEL} → {destination_id}")
    else:
        print(f"❌ Signal dropped after retries")


# ===================================================================
# MAIN
# ===================================================================

async def main():
    await user_client.connect()
    if not await user_client.is_user_authorized():
        print("❌ ERROR: Session string invalid or expired!")
        return
    print("✅ Userbot connected.")
    print(f"📡 Source: {SOURCE_CHANNEL}")

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("🌐 Translation: ALWAYS SPANISH — no exceptions")
    print("🚫 Promotional messages: BLOCKED")
    print("🛡️  Error 500 messages: BLOCKED at source")
    print("🔄  Auto-retry on server errors: ENABLED")
    print(f"📡 {SOURCE_CHANNEL} → {DESTINATION_CHANNEL}\n")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected(),
    )


asyncio.run(main())
