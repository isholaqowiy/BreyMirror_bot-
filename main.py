import os
import re
import sys
import fcntl
import asyncio
from collections import deque, OrderedDict
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
    FloodWaitError,
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

# ---------------------------------------------------------------------------
# SINGLE-INSTANCE LOCK
# ---------------------------------------------------------------------------
# Prevents two copies of this bot running at once on the same machine
# (which causes duplicate/garbled delivery and session instability).
_LOCK_PATH = "/tmp/brey_signal_bot.lock"
_lock_file = open(_LOCK_PATH, "w")
try:
    fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    print("❌ Another instance of this bot is already running "
          f"(lock file: {_LOCK_PATH}). Stop it before starting a new one.")
    sys.exit(1)

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

# --- WORD REPLACEMENTS (final normalization pass) ---
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

# --- ERROR TEXTS TO STRIP FROM SOURCE MESSAGES ---
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

# --- SIGNATURES THAT MEAN "THE TRANSLATOR ITSELF FAILED", NOT A REAL
# --- TRANSLATION. When Google's free translate endpoint is
# --- overloaded/rate-limited it can return an HTML/text error page
# --- INSTEAD OF raising an exception — deep_translator then happily
# --- hands that back as if it were a successful translation. This is
# --- exactly what leaked into the destination channel as literal
# --- "Error 500 (Server Error)..." text. Any translator result that
# --- matches one of these is treated as a failed call, never as
# --- real content.
TRANSLATE_ERROR_SIGNATURES = [
    r"error\s*\d{3}",
    r"server error",
    r"that'?s an error",
    r"there was an error",
    r"please try again later",
    r"that'?s all we know",
    r"too many requests",
    r"rate limit",
    r"bad gateway",
    r"service unavailable",
    r"internal server error",
]
_TRANSLATE_ERROR_RE = re.compile(
    "|".join(TRANSLATE_ERROR_SIGNATURES), flags=re.IGNORECASE
)


def _looks_like_translation_error(text):
    return bool(text) and bool(_TRANSLATE_ERROR_RE.search(text))


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

# --- VALID SIGNAL PATTERNS ---
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
    r"\brunning\b",
    r"\bseguimos\b",
    r"\bcierra\b",
    r"\bdentro\b",
    r"\bpagando\b",
    r"close.*position",
    r"close first",
    r"close fully",
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

print("Starting Brey Trading Signal Bot...")

user_client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH
)
bot_client = TelegramClient(StringSession(), API_ID, API_HASH)

# ---------------------------------------------------------------------------
# TRANSLATION ENGINE
# ---------------------------------------------------------------------------
_PROTECT_PATTERNS = [
    r'"[^"]*"',            # quoted labels e.g. "SCALP"
    r"XAU/?USD",
    r"\bTP\s*\d\b",
    r"\bSL\b",
    r"\bSCALP\b",
    r"@\w+",
    r"https?://\S+",
    r"\d{1,6}(?:[.,]\d+)?",
]
_PROTECT_RE = re.compile(
    "|".join(_PROTECT_PATTERNS), flags=re.IGNORECASE
)

PRE_TRANSLATE_PHRASES = [
    (r'\btrail\s+sl\s+to\s+maximize\s+profits?\b', 'mover sl para maximizar ganancias'),
    (r'\btrail\s+sl\b', 'mover sl'),
    (r'\bto\s+maximize\s+profits?\b', 'para maximizar ganancias'),
    (r'\bmaximize\s+profits?\b', 'maximizar ganancias'),
    (r'\bfirst\s+entry\b', 'primera entrada'),
    (r'\bsecond\s+entry\b', 'segunda entrada'),
    (r'\bthird\s+entry\b', 'tercera entrada'),
    (r'\bclose\s+first\s+position\b', 'cerrar primera posición'),
    (r'\bclose\s+second\s+position\b', 'cerrar segunda posición'),
    (r'\bclose\s+position\b', 'cerrar posición'),
    (r'\bclose\s+fully\s+now\b', 'cerrar completamente ahora'),
    (r'\bclose\s+fully\b', 'cerrar completamente'),
    (r'\bfully\b', 'completamente'),
    (r'\bbreak\s*even\b', 'punto de equilibrio'),
    (r'\bsl\s+hit\b', 'sl alcanzado'),
    (r'\bonto\s+next\s+opportunity\b', 'a la siguiente oportunidad'),
    (r'\bnext\s+opportunity\b', 'siguiente oportunidad'),
    (r'\bmove\s+sl\s+to\s+entry\b', 'mover sl a la entrada'),
    (r'\bmove\s+sl\b', 'mover sl'),
    (r'\bsignal\s+ready\b', 'señal lista'),
    (r'\btake\s*profit\b', 'tomar ganancias'),
    (r'\bstop\s*loss\b', 'stop loss'),
    (r'\bsecure\b', 'asegurar'),
    (r'\bbanked\b', 'aseguradas'),
    (r"\bthat'?s\b", 'eso son'),
    (r'\brunning\b', 'corriendo'),
    (r'\brisk\s+free\b', 'libre de riesgo'),
    (r'\bconsidering\s+this\s+a\s+separate\s+trade\b', 'considerando esto una operación separada'),
    (r'\bseparate\s+trade\b', 'operación separada'),
    (r'\balready\s+having\b', 'ya teniendo'),
    (r'\bhits\b', 'alcanzado'),
    (r'\bhit\b', 'alcanzado'),
    (r'\bpositions\b', 'posiciones'),
    (r'\bposition\b', 'posición'),
    (r'\bentries\b', 'entradas'),
    (r'\bentry\b', 'entrada'),
    (r'\bfirst\b', 'primera'),
    (r'\bsecond\b', 'segunda'),
    (r'\bthird\b', 'tercera'),
    (r'\bbuy\b', 'comprar'),
    (r'\bsell\b', 'vender'),
]


def _case_preserve_replace(replacement):
    def _repl(match):
        matched = match.group(0)
        if matched.isupper():
            return replacement.upper()
        if matched[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement
    return _repl


def _has_letters(s):
    return bool(re.search(r"[A-Za-zÀ-ÿ]", s))


# Cap how many Google Translate calls run at once, bot-wide. Firing
# every line of every message at once was likely what pushed Google's
# free endpoint into rate-limiting us and returning error pages.
_TRANSLATE_SEMAPHORE = asyncio.Semaphore(3)

# Small bounded cache so an identical recurring line (common in these
# channels — the same template phrases repeat constantly) doesn't
# need a fresh network call every single time.
_TRANSLATION_CACHE = OrderedDict()
_TRANSLATION_CACHE_MAX = 500


def _cache_get(key):
    if key in _TRANSLATION_CACHE:
        _TRANSLATION_CACHE.move_to_end(key)
        return _TRANSLATION_CACHE[key]
    return None


def _cache_set(key, value):
    _TRANSLATION_CACHE[key] = value
    _TRANSLATION_CACHE.move_to_end(key)
    if len(_TRANSLATION_CACHE) > _TRANSLATION_CACHE_MAX:
        _TRANSLATION_CACHE.popitem(last=False)


def _translate_sync(text_to_translate):
    """Blocking network call — always run via asyncio.to_thread."""
    return GoogleTranslator(source="auto", target="es").translate(
        text_to_translate
    )


async def _translate_async(text_to_translate, timeout=8.0, max_attempts=2):
    """Non-blocking, timed, retried, and VALIDATED translation call.
    Never returns an error page as if it were a translation — if the
    result looks like a failure signature, it's discarded and
    retried, and if all attempts fail, returns None so the caller
    falls back to safe (dictionary-only) text instead of garbage."""
    for attempt in range(1, max_attempts + 1):
        result = None
        try:
            async with _TRANSLATE_SEMAPHORE:
                result = await asyncio.wait_for(
                    asyncio.to_thread(_translate_sync, text_to_translate),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            print(f"⚠️ Translation timed out (attempt {attempt}/{max_attempts}).")
        except (NotValidPayload, TranslationNotFound):
            return None
        except Exception as e:
            print(f"⚠️ Translation error (attempt {attempt}/{max_attempts}): {e}")

        if result and _looks_like_translation_error(result):
            print("⚠️ Translator returned an error page instead of a "
                  "translation — discarding and retrying.")
            result = None

        if result and result.strip():
            return result

        if attempt < max_attempts:
            await asyncio.sleep(1.5 * attempt)

    return None


async def translate_line_to_spanish(line):
    stripped = line.strip()
    if not stripped or not _has_letters(stripped):
        return line

    # Step 1: deterministic phrase dictionary first.
    working = stripped
    for pattern, replacement in PRE_TRANSLATE_PHRASES:
        working = re.sub(
            pattern, _case_preserve_replace(replacement),
            working, flags=re.IGNORECASE
        )

    # Step 2: protect anything that must stay 100% literal.
    protected = []

    def _stash(match):
        protected.append(match.group(0))
        return f"§{len(protected) - 1}§"

    placeholder_text = _PROTECT_RE.sub(_stash, working)
    expected_tokens = {f"§{i}§" for i in range(len(protected))}

    # Step 3: only call the translator if there's real translatable
    # content left, and only trust the result if EVERY protected
    # token is still present afterward (if Google drops/mangles a
    # placeholder, whatever was next to it gets silently lost — this
    # is what turned "Tp3 running +180 pips" into just "TP3").
    remaining = re.sub(r"§\d+§", "", placeholder_text)
    if _has_letters(remaining):
        cached = _cache_get(placeholder_text)
        if cached is not None:
            translated = cached
        else:
            raw = await _translate_async(placeholder_text)
            found_tokens = set(re.findall(r"§\d+§", raw)) if raw else set()
            if raw and raw.strip() and found_tokens == expected_tokens:
                translated = raw
                _cache_set(placeholder_text, translated)
            else:
                if raw:
                    print("⚠️ Translation lost/altered protected tokens — "
                          "using safe fallback text instead.")
                translated = placeholder_text
    else:
        translated = placeholder_text

    # Step 4: restore protected tokens exactly as they were.
    def _restore(match):
        idx = int(match.group(1))
        return protected[idx] if idx < len(protected) else match.group(0)

    translated = re.sub(r"§(\d+)§", _restore, translated)

    leading = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]
    return f"{leading}{translated}{trailing}"


async def translate_to_spanish(text):
    if not text:
        return text
    if not SETTINGS.get("ai_translate", True):
        return text
    lines = text.split('\n')
    translated_lines = await asyncio.gather(
        *(translate_line_to_spanish(line) for line in lines)
    )
    return '\n'.join(translated_lines)


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


async def clean_message(text):
    """Remove names/links/errors → translate → normalize → scrub
    error text AGAIN as a final defense-in-depth pass."""
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

    # Translate (async, non-blocking, throttled, validated).
    text = await translate_to_spanish(text)

    # Defense in depth: strip any translator-error text that might
    # still have slipped through, even after per-line validation.
    text = remove_error_texts(text)

    # Final normalization / safety net pass.
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)

    text = re.sub(r'\bxauusd\b', 'XAUUSD', text, flags=re.IGNORECASE)
    text = re.sub(r'\bxau/usd\b', 'XAU/USD', text, flags=re.IGNORECASE)
    text = re.sub(r'\btp(\d)\b', r'TP\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsl\b', 'SL', text, flags=re.IGNORECASE)
    text = re.sub(r'\bscalp\b', 'SCALP', text, flags=re.IGNORECASE)
    text = re.sub(r'\bFIRST\b', 'PRIMERA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bSECOND\b', 'SEGUNDA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bTHIRD\b', 'TERCERA', text, flags=re.IGNORECASE)

    # Clean empty / separator-only lines.
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


async def process_message(raw_text):
    """Clean → translate → sign."""
    if not raw_text:
        return None
    text = await clean_message(raw_text)
    if not text:
        return None
    return text + SIGNATURE


# -------------------------------------------------------------------
# DELIVERY WITH RETRY / FLOOD-WAIT HANDLING
# -------------------------------------------------------------------
async def send_with_retry(coro_factory, max_retries=3):
    attempt = 0
    while True:
        try:
            return await coro_factory()
        except FloodWaitError as e:
            wait_s = e.seconds + 1
            print(f"⏳ FloodWait: sleeping {wait_s}s before retry...")
            await asyncio.sleep(wait_s)
        except Exception as e:
            attempt += 1
            print(f"⚠️ Send attempt {attempt}/{max_retries} failed: {e}")
            if attempt >= max_retries:
                print("❌ Giving up on this message after max retries.")
                raise
            await asyncio.sleep(2 * attempt)


# -------------------------------------------------------------------
# DEDUP GUARD
# -------------------------------------------------------------------
_seen_messages = deque(maxlen=1000)
_seen_messages_set = set()


def _already_processed(chat_id, message_id):
    key = (chat_id, message_id)
    if key in _seen_messages_set:
        return True
    _seen_messages.append(key)
    _seen_messages_set.add(key)
    if len(_seen_messages) == _seen_messages.maxlen:
        _seen_messages_set.intersection_update(_seen_messages)
    return False


# -------------------------------------------------------------------
# SOURCE→DESTINATION MESSAGE MAP (for syncing later edits)
# -------------------------------------------------------------------
# When the source channel EDITS an already-posted message (e.g.
# updating "TP3 running" with new pip counts, or fixing a typo),
# Telegram sends an edit event, not a new message. Without this map
# there is no way to know which destination message to update, so
# those edits were silently never reaching the destination channel.
_MESSAGE_ID_MAP = OrderedDict()
_MESSAGE_ID_MAP_MAX = 2000


def _remember_destination(source_msg_id, destination_chat_id, destination_msg_id):
    _MESSAGE_ID_MAP[source_msg_id] = (destination_chat_id, destination_msg_id)
    _MESSAGE_ID_MAP.move_to_end(source_msg_id)
    if len(_MESSAGE_ID_MAP) > _MESSAGE_ID_MAP_MAX:
        _MESSAGE_ID_MAP.popitem(last=False)


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
            "👋 Bienvenido a Brey Trading Signal Bot!\n\n"
            "📡 Copiando señales de Gold automáticamente\n"
            "➡️ Destino: BREY TRADING FX VIP\n\n"
            "🇪🇸 Idioma: Español (fijo)\n"
            "🤖 Traducción: Automática (validada, sin bloqueo)\n"
            "✏️ Ediciones del canal fuente: Sincronizadas\n"
            "🚫 Mensajes promocionales: Bloqueados\n"
            "📋 Señales: Copiadas limpiamente\n\n"
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
            "➡️ /pause - Pausar bot\n"
            "➡️ /resume - Reanudar bot\n"
            "➡️ /ping - Verificar bot activo\n"
            "➡️ /addword vieja:nueva - Reemplazar\n"
            "➡️ /removeword palabra - Quitar\n"
            "➡️ /wordlist - Ver reemplazos\n"
            "➡️ /blockword palabra - Bloquear\n"
            "➡️ /unblockword palabra - Desbloquear\n"
            "➡️ /blocklist - Ver bloqueadas\n"
            "➡️ /channels - Ver canales\n"
        )

    elif command == "/status":
        paused = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        await event.respond(
            f"📊 Estado:\n\n"
            f"• Estado: {paused}\n"
            f"• Idioma: Español (fijo)\n"
            f"• Traducción: ON (validada, sin bloqueo)\n"
            f"• Canal fuente: {SOURCE_CHANNEL}\n"
            f"• Canal destino: {DESTINATION_CHANNEL}\n"
            f"• Reemplazos: "
            f"{len(SETTINGS['custom_replacements'])}\n"
            f"• Palabras bloqueadas: "
            f"{len(SETTINGS['blocked_words'])}\n"
            f"• Mensajes vistos (dedup): {len(_seen_messages_set)}\n"
            f"• Mensajes con ediciones sincronizadas: {len(_MESSAGE_ID_MAP)}\n\n"
            f"✅ Bot funcionando correctamente"
        )

    elif command == "/ping":
        await event.respond(
            "🏓 Pong!\n"
            "✅ Bot activo y funcionando.\n"
            f"📡 Monitoreando: {SOURCE_CHANNEL}"
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

    elif full_text.lower().startswith("/addword "):
        try:
            parts = full_text[9:].split(":")
            if len(parts) == 2:
                old_word = parts[0].strip()
                new_word = parts[1].strip()
                SETTINGS["custom_replacements"][old_word] = new_word
                await event.respond(f"✅ {old_word} → {new_word}")
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
                 for k, v in SETTINGS["custom_replacements"].items()]
            )
            await event.respond(f"📝 Reemplazos:\n\n{replacements}")
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
            await event.respond("⚠️ Ya bloqueado.")

    elif full_text.lower().startswith("/unblockword "):
        word = full_text[13:].strip()
        if word in SETTINGS["blocked_words"]:
            SETTINGS["blocked_words"].remove(word)
            await event.respond(f"✅ Desbloqueado: {word}")
        else:
            await event.respond("❌ No está en la lista.")

    elif command == "/blocklist":
        if SETTINGS["blocked_words"]:
            words = "\n".join(
                [f"• {w}" for w in SETTINGS["blocked_words"]]
            )
            await event.respond(f"🚫 Bloqueadas:\n\n{words}")
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

    if data == "noop":
        await event.answer("El idioma está fijo en Español.")

    elif data == "toggle_pause":
        SETTINGS["paused"] = not SETTINGS["paused"]
        status = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        await event.answer(f"Bot: {status}")
        await safe_edit(
            event, "🎛 Panel de Control:",
            buttons=get_main_menu_buttons()
        )

    elif data == "show_status":
        paused = (
            "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        )
        await event.answer("Estado!")
        await safe_edit(
            event,
            f"📊 Estado:\n\n"
            f"• Estado: {paused}\n"
            f"• Idioma: Español (fijo)\n"
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
            f"• ID Fuente: {SOURCE_CHANNEL}\n\n"
            f"• Destino: BREY TRADING FX VIP\n"
            f"• ID Destino: {DESTINATION_CHANNEL}",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "back_menu":
        await safe_edit(
            event, "🎛 Panel de Control:",
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

    dedup_key_id = event.messages[0].id if event.messages else None
    if dedup_key_id and _already_processed(source_id, f"album:{dedup_key_id}"):
        print("⏭️ Skipped album: duplicate")
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
            caption = await process_message(raw)
            break

    media_files = [
        msg.media for msg in event.messages
        if is_photo_message(msg)
    ]

    if media_files:
        try:
            sent = await send_with_retry(
                lambda: user_client.send_file(
                    destination_id, media_files, caption=caption
                )
            )
            if sent and event.messages:
                first_sent = sent[0] if isinstance(sent, list) else sent
                _remember_destination(
                    event.messages[0].id, destination_id, first_sent.id
                )
            print(f"✅ Album sent → {destination_id}")
        except Exception as e:
            print(f"❌ Album failed after retries: {e}")


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
        return  # handled by album_handler

    if _already_processed(source_id, event.message.id):
        print("⏭️ Skipped: duplicate message id")
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
            print(f"⏭️ Skipped: not a valid signal: {raw_text[:50]}")
            return

    final_text = await process_message(raw_text) if raw_text else None

    if raw_text and not final_text:
        print("⏭️ Skipped: text empty after cleaning")
        return

    try:
        sent = None
        if is_photo:
            sent = await send_with_retry(
                lambda: user_client.send_file(
                    destination_id, event.message.media, caption=final_text
                )
            )
        elif has_media and not is_photo:
            if not raw_text:
                print("⏭️ Skipped: non-photo no text")
                return
            sent = await send_with_retry(
                lambda: user_client.send_message(destination_id, final_text)
            )
        else:
            if not final_text:
                return
            sent = await send_with_retry(
                lambda: user_client.send_message(destination_id, final_text)
            )

        if sent is not None:
            _remember_destination(event.message.id, destination_id, sent.id)

        print(f"✅ Signal: {source_id} → {destination_id}")
    except Exception as e:
        print(f"❌ Delivery failed after retries: {e}")


# -------------------------------------------------------------------
# EDIT SYNC HANDLER
# -------------------------------------------------------------------
# When the source channel edits a message it already posted (very
# common for "TPx running +N pips" updates), sync that edit onto the
# matching destination message instead of leaving it stale/incomplete.
@user_client.on(events.MessageEdited(chats=[SOURCE_CHANNEL]))
async def edit_sync_handler(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    mapping = _MESSAGE_ID_MAP.get(event.message.id)
    if not mapping:
        print("⏭️ Skipped edit: no matching destination message on record")
        return
    dest_chat_id, dest_msg_id = mapping

    if is_noforwards(event.message):
        return

    raw_text = event.message.message
    if raw_text and is_promotional(raw_text):
        return
    if raw_text and is_blocked_word_found(raw_text):
        return

    final_text = await process_message(raw_text) if raw_text else None
    if not final_text:
        return

    try:
        await send_with_retry(
            lambda: user_client.edit_message(dest_chat_id, dest_msg_id, final_text)
        )
        print(f"✏️ Edit synced: {source_id} → {destination_id}")
    except Exception as e:
        print(f"❌ Edit sync failed after retries: {e}")


# -------------------------------------------------------------------
# RESILIENT CLIENT RUNNER — never sleeps, never gives up
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
                    print(f"❌ {name} session invalid/expired!")
                    print("Please generate a new session string.")
                    return

            print(f"✅ {name} connected.")
            backoff = 5
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
            return
    except (
        SessionExpiredError,
        SessionRevokedError,
        AuthKeyUnregisteredError,
    ) as e:
        print(f"❌ Session error: {e}")
        return

    print("✅ Userbot connected and authorized.")
    print(f"📡 Monitoring: {SOURCE_CHANNEL}")

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("🇪🇸 Output: Spanish (fixed)")
    print("🤖 Translation: async, throttled, validated (rejects error pages)")
    print("✏️ Edit sync: ACTIVE")
    print("🔒 Single-instance lock: ACTIVE")
    print("🔁 Dedup guard: ACTIVE")
    print("♻️ Retry + FloodWait handling: ACTIVE")
    print("🔄 Auto-reconnect: ENABLED (never stops)")
    print(f"📡 {SOURCE_CHANNEL} → {DESTINATION_CHANNEL}\n")

    await asyncio.gather(
        run_client_forever(user_client, "Userbot"),
        run_client_forever(
            bot_client, "Bot", start_kwargs={"bot_token": BOT_TOKEN}
        ),
    )


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Unexpected top-level crash: {e}")
            print("🔄 Restarting bot in 10 seconds...")
            import time
            time.sleep(10)

