import os
import re
import time
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

try:
    import requests  # installed together with deep_translator
except ImportError:  # pragma: no cover
    requests = None

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
# (English + Spanish versions, straight and curly apostrophes.
#  These are also what Google's error page looks like when the
#  translator gets blocked / rate limited.)
ERROR_TEXTS_TO_REMOVE = [
    r"Error\s*500\s*\(Server Error\)[^\n]*",
    r"That['’]?s an error\.?[^\n]*",
    r"There was an error\.?[^\n]*",
    r"Please try again later\.?[^\n]*",
    r"That['’]?s all we know\.?[^\n]*",
    r"Error\s*\d+[^\n]*",
    r"Server Error[^\n]*",
    r"HTTP Error[^\n]*",
    r"Connection Error[^\n]*",
    r"Request Failed[^\n]*",
    r"Timed out[^\n]*",
    r"Es un error\.[^\n]*",
    r"Se ha producido un error[^\n]*",
    r"Ha ocurrido un error[^\n]*",
    r"Vuelve a intentarlo[^\n]*",
    r"Eso es todo lo que sabemos[^\n]*",
    r"Error (del|de) servidor[^\n]*",
]

# Used to detect a translator that returned an error page instead of a
# real translation.
_ERROR_SIGNATURE_RE = re.compile(
    r"Error\s*500|\(Server Error\)|That['’]?s an error|"
    r"There was an error|Please try again later|"
    r"That['’]?s all we know|Se ha producido un error|"
    r"Eso es todo lo que sabemos|Vuelve a intentarlo",
    re.IGNORECASE,
)

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
    # Images/screenshots are BLOCKED by default (client request).
    # Can be switched with /images on | /images off or the menu button.
    "allow_images": False,
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

# --- TRANSLATION TUNING ---
# Backends are tried in this order. A message is only sent when one of
# them returns a COMPLETE translation (no leftover English words).
TRANSLATION_BACKENDS = ["google", "gtx"]
BACKEND_RETRIES = {"google": 3, "gtx": 2}
BACKEND_CHUNK_LIMIT = {"google": 4000, "gtx": 1200}
TRANSLATE_RETRY_DELAY = 1.5   # seconds, multiplied by attempt number
GTX_URL = "https://translate.googleapis.com/translate_a/single"

# English function/chat words that must NOT survive in the Spanish
# output. Trading terms (SL, TP, XAUUSD, pips, stop loss...) are fine.
ENGLISH_MARKER_WORDS = {
    "the", "we", "you", "your", "our", "is", "was", "were", "will",
    "this", "that", "these", "those", "with", "for", "and", "from",
    "but", "when", "then", "if", "it", "its", "be", "been", "not",
    "just", "please", "guys", "here", "there", "what", "where", "how",
    "why", "of", "to", "in", "on", "at", "price", "coming", "now",
    "all", "close", "closed", "closing", "set", "position",
    "positions", "it's", "that's", "let's", "don't", "can't",
    "won't", "i'm",
}

print("Starting Brey Trading Signal Bot...")

user_client = TelegramClient(
    StringSession(SESSION_STRING), API_ID, API_HASH
)
bot_client = TelegramClient(StringSession(), API_ID, API_HASH)

_PROTECT_PATTERNS = [
    r"XAU/?USD",
    r"\bTP\s*\d\b",
    r"\bSL\b",
    r"\d{3,5}(?:\.\d+)?",
]
_PROTECT_RE = re.compile(
    "|".join(_PROTECT_PATTERNS), flags=re.IGNORECASE
)
_PLACEHOLDER_RE = re.compile(r"§\s*(\d+)\s*§")

_translate_lock = None


class TranslationIncomplete(Exception):
    """Raised when no backend could fully translate a message."""


# English → Spanish trading phrases (applied when output is Spanish)
PHRASE_MAP = [
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

# Safety net: repairs English words/phrases that a translator left
# behind. Only used on text that already went through a translator.
_OFFLINE_PHRASES = [
    (r'\bwhen\s+(?:the\s+)?price\s+(?:is\s+)?'
     r'(?:coming|comes?|arrives?|reaches|reach|hits?)\b',
     'cuando el precio llegue'),
    (r'\bwhen\s+(?:the\s+)?price\s+(?:is\s+)?(?:back|returns?)\b',
     'cuando el precio regrese'),
    (r'\bclose\s+all\s+positions?\b', 'cerrar todas las posiciones'),
    (r'\bclose\s+(?:the\s+)?first\s+position\b',
     'cerrar la primera posición'),
    (r'\bclose\s+(?:the\s+)?positions?\b', 'cerrar la posición'),
    (r'\bwe\s+close\b', 'cerramos'),
    (r'\b(sl)\s+to\s+(?:be|break\s*even|punto de equilibrio)\b',
     r'\1 a punto de equilibrio'),
    (r'\b(tp\s*\d)\s+hit\b', r'\1 alcanzado'),
]
_OFFLINE_WORDS = [
    (r'\bprice\b', 'precio'),
    (r'\bnow\b', 'ahora'),
    (r'\bwhen\b', 'cuando'),
    (r'\bclosed\b', 'cerrado'),
    (r'\bclose\b', 'cerrar'),
    (r'\bpositions\b', 'posiciones'),
    (r'\bposition\b', 'posición'),
    (r'\bset\b', 'coloquen'),
    (r'\bwait\b', 'esperen'),
    (r'\bprofits\b', 'ganancias'),
    (r'\bprofit\b', 'ganancia'),
    (r'\bwe\b', 'nosotros'),
]


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


def has_error_signature(text):
    """True if the text looks like a Google/HTTP error page."""
    if not text:
        return False
    return bool(_ERROR_SIGNATURE_RE.search(text))


def _has_letters(s):
    return bool(re.search(r"[A-Za-zÀ-ÿ]", s))


# -------------------------------------------------------------------
# TRANSLATION ENGINE
# -------------------------------------------------------------------
def english_leftovers(text):
    """English chat words still present in the (Spanish) text."""
    if not text:
        return []
    words = re.findall(r"[A-Za-z'’]+", text.lower())
    found = set()
    for w in words:
        w = w.replace("’", "'")
        if w in ENGLISH_MARKER_WORDS:
            found.add(w)
    return sorted(found)


def offline_repair(text):
    """Fix English words a translator left behind (Spanish output)."""
    if not text:
        return text
    out = []
    for line in text.split('\n'):
        original = line
        for pattern, repl in _OFFLINE_PHRASES:
            line = re.sub(pattern, repl, line, flags=re.IGNORECASE)
        for pattern, repl in _OFFLINE_WORDS:
            line = re.sub(pattern, repl, line, flags=re.IGNORECASE)
        if line != original:
            stripped = line.lstrip()
            if stripped and stripped[0].isalpha() and stripped[0].islower():
                indent = line[: len(line) - len(stripped)]
                line = indent + stripped[0].upper() + stripped[1:]
        out.append(line)
    return '\n'.join(out)


def normalize_trading_terms(text):
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
    return text


def finalize_translation(text, repair=True):
    """Strip error text, normalize trading terms, Spanish phrases."""
    text = remove_error_texts(text)
    text = normalize_trading_terms(text)
    if SETTINGS["target_language"] == "es":
        for pattern, replacement in PHRASE_MAP:
            text = re.sub(
                pattern, replacement, text, flags=re.IGNORECASE
            )
        if repair:
            text = offline_repair(text)
        text = normalize_trading_terms(text)
    return text


def _restore_tokens(text, protected):
    """Put protected tickers/numbers back. Returns (text, all_ok)."""
    found = set()

    def _restore(match):
        idx = int(match.group(1))
        if idx < len(protected):
            found.add(idx)
            return protected[idx]
        return ""

    restored = _PLACEHOLDER_RE.sub(_restore, text)
    return restored, len(found) == len(protected)


def _split_chunks(text, limit):
    """Split text into chunks (on line boundaries) under the limit."""
    chunks = []
    current = []
    size = 0
    for line in text.split('\n'):
        add = len(line) + 1
        if current and size + add > limit:
            chunks.append('\n'.join(current))
            current = []
            size = 0
        current.append(line)
        size += add
    if current:
        chunks.append('\n'.join(current))
    return chunks


def _gtx_translate(text, target):
    """Google's JSON translate endpoint (independent of the HTML
    page that deep_translator scrapes)."""
    if requests is None:
        raise RuntimeError("requests not available")
    resp = requests.get(
        GTX_URL,
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": target,
            "dt": "t",
            "q": text,
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(
        seg[0] for seg in data[0] if seg and seg[0]
    )


def _call_backend(backend, text, target):
    if backend == "google":
        return GoogleTranslator(
            source="auto", target=target
        ).translate(text)
    if backend == "gtx":
        return _gtx_translate(text, target)
    raise ValueError(f"unknown backend: {backend}")


def _translate_chunk_sync(chunk, target, backend):
    """
    Translate one chunk with one backend (blocking - run in a thread).
    Protects tickers/numbers, retries on failure, and REJECTS
    translator error pages. Returns translated text, or None if all
    attempts failed.
    """
    if not chunk.strip():
        return chunk

    protected = []

    def _stash(match):
        protected.append(match.group(0))
        return f"§{len(protected) - 1}§"

    placeholder = _PROTECT_RE.sub(_stash, chunk)

    # Nothing to translate (only numbers / emojis / symbols)
    if not _has_letters(placeholder):
        return chunk

    source_has_error = has_error_signature(chunk)
    retries = BACKEND_RETRIES.get(backend, 2)

    for attempt in range(1, retries + 1):
        try:
            translated = _call_backend(backend, placeholder, target)

            if not translated or not translated.strip():
                raise ValueError("empty translation")

            if has_error_signature(translated) and not source_has_error:
                raise ValueError("translator returned an error page")

            restored, ok = _restore_tokens(translated, protected)
            if ok:
                return restored

            # Placeholders got mangled -> try without protection and
            # accept only if every ticker/number survived.
            print("⚠️ Placeholders lost, retrying unprotected")
            raw = _call_backend(backend, chunk, target)
            if (
                raw
                and raw.strip()
                and (source_has_error or not has_error_signature(raw))
                and all(
                    tok.lower() in raw.lower() for tok in protected
                )
            ):
                return raw
            raise ValueError("tickers/numbers not preserved")

        except Exception as e:
            print(
                f"⚠️ Translation [{backend}] attempt {attempt}/"
                f"{retries} failed: {e}"
            )
            if attempt < retries:
                time.sleep(TRANSLATE_RETRY_DELAY * attempt)

    return None


async def translate_text(text, backend):
    """Translate with one backend without blocking the event loop.
    Returns None if any part failed."""
    global _translate_lock
    if _translate_lock is None:
        _translate_lock = asyncio.Lock()

    target = SETTINGS["target_language"]
    limit = BACKEND_CHUNK_LIMIT.get(backend, 1200)
    loop = asyncio.get_running_loop()
    output = []

    async with _translate_lock:
        for chunk in _split_chunks(text, limit):
            result = await loop.run_in_executor(
                None, _translate_chunk_sync, chunk, target, backend
            )
            if result is None:
                return None
            output.append(result)

    return '\n'.join(output)


async def translate_verified(text):
    """
    Returns a COMPLETE translation or raises TranslationIncomplete.
    Never returns half-English / half-Spanish text.
    """
    if not text:
        return text

    if not SETTINGS.get("ai_translate", True):
        return finalize_translation(text, repair=False)

    reasons = []
    for backend in TRANSLATION_BACKENDS:
        translated = await translate_text(text, backend)
        if translated is None:
            reasons.append(f"{backend}: failed")
            continue

        final = finalize_translation(translated)
        leftovers = (
            english_leftovers(final)
            if SETTINGS["target_language"] == "es" else []
        )
        if not leftovers:
            return final

        print(
            f"⚠️ [{backend}] English words left: "
            f"{', '.join(leftovers)} → trying next backend"
        )
        reasons.append(
            f"{backend}: English left ({', '.join(leftovers)})"
        )

    raise TranslationIncomplete("; ".join(reasons))


async def notify_owner(text):
    try:
        await bot_client.send_message(OWNER_ID, text)
    except Exception as e:
        print(f"⚠️ Could not notify owner: {e}")


async def clean_message(text):
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

    # Translate completely (raises TranslationIncomplete on failure),
    # then strip errors / normalize trading terms / Spanish phrases
    text = await translate_verified(text)

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


async def process_message(raw_text):
    if not raw_text:
        return None

    try:
        text = await clean_message(raw_text)
    except TranslationIncomplete as e:
        print(f"❌ Translation incomplete, message NOT sent: {e}")
        await notify_owner(
            "⚠️ Mensaje NO enviado: no se pudo traducir por "
            "completo.\n\n"
            f"Original:\n{raw_text[:1500]}\n\n"
            "Revisa los logs del servidor para ver el motivo."
        )
        return None

    if not text:
        return None
    # Final safety net: never send translator/server error text
    if has_error_signature(text) and not has_error_signature(raw_text):
        print("⏭️ Skipped: error text detected after cleaning")
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
    images_status = (
        "✅ ON" if SETTINGS["allow_images"] else "🛑 OFF"
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
            f"🖼 Images: {images_status}",
            "toggle_images"
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
            "🚫 Spam y errores: Bloqueados\n"
            "🚫 Imágenes: Bloqueadas\n\n"
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
            "➡️ /images on - Permitir imágenes\n"
            "➡️ /images off - Bloquear imágenes\n"
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
        images = (
            "✅ ON" if SETTINGS["allow_images"] else "🛑 OFF"
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
            f"• Imágenes: {images}\n"
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

    elif command == "/images on":
        SETTINGS["allow_images"] = True
        await event.respond("✅ Imágenes PERMITIDAS.")

    elif command == "/images off":
        SETTINGS["allow_images"] = False
        await event.respond(
            "🛑 Imágenes BLOQUEADAS.\n"
            "Solo se enviará texto de señales."
        )

    elif command.startswith("/language "):
        lang = command.split("/language ")[1].strip()
        if lang in LANGUAGES.values():
            SETTINGS["target_language"] = lang
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

    elif data == "toggle_images":
        SETTINGS["allow_images"] = not SETTINGS["allow_images"]
        status = (
            "✅ ON" if SETTINGS["allow_images"] else "🛑 OFF"
        )
        await event.answer(f"Imágenes: {status}")
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
        images = (
            "✅ ON" if SETTINGS["allow_images"] else "🛑 OFF"
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
            f"• Imágenes: {images}\n"
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

    raw_caption = None
    for msg in event.messages:
        if msg.message:
            raw_caption = msg.message
            break

    if raw_caption:
        if is_promotional(raw_caption):
            print("⏭️ Skipped album: promotional")
            return
        if is_blocked_word_found(raw_caption):
            print("⏭️ Skipped album: blocked word")
            return

    # --- IMAGES BLOCKED: never send the pictures ---
    if not SETTINGS["allow_images"]:
        if raw_caption and is_valid_signal(raw_caption):
            final_text = await process_message(raw_caption)
            if final_text:
                try:
                    await user_client.send_message(
                        destination_id, final_text
                    )
                    print(
                        f"✅ Album caption (text only) → "
                        f"{destination_id}"
                    )
                except Exception as e:
                    print(f"❌ Album text failed: {e}")
            else:
                print("⏭️ Skipped album: caption not sent")
        else:
            print("⏭️ Skipped album: images blocked")
        return

    caption = (
        await process_message(raw_caption) if raw_caption else None
    )

    # Never send a captioned album without its (translated) caption
    if raw_caption and not caption:
        print("⏭️ Skipped album: caption not sent")
        return

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

    # --- IMAGES BLOCKED: photo without text is never forwarded ---
    if is_photo and not SETTINGS["allow_images"] and not raw_text:
        print("⏭️ Skipped: image blocked")
        return

    if raw_text and is_promotional(raw_text):
        print("⏭️ Skipped: promotional")
        return

    if raw_text and is_blocked_word_found(raw_text):
        print("⏭️ Skipped: blocked word")
        return

    # Text must look like a real gold signal. Only photos that are
    # explicitly allowed keep the old behaviour (caption not checked).
    photo_allowed = is_photo and SETTINGS["allow_images"]
    if raw_text and not photo_allowed:
        if not is_valid_signal(raw_text):
            print(
                f"⏭️ Skipped: not valid signal: "
                f"{raw_text[:40]}"
            )
            return

    final_text = (
        await process_message(raw_text) if raw_text else None
    )

    if raw_text and not final_text:
        print("⏭️ Skipped: not sent (empty / not fully translated)")
        return

    try:
        if photo_allowed:
            await user_client.send_file(
                destination_id,
                event.message.media,
                caption=final_text
            )
        else:
            # Text only (photos are never sent while blocked)
            if not final_text:
                print("⏭️ Skipped: non-photo no text")
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
    print("🤖 Translation: 2 backends + completeness check")
    print("🚫 Error texts: REMOVED")
    print("🚫 Images: BLOCKED (toggle with /images on|off)")
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
