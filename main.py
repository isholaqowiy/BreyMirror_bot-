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
# Maps source channel IDs → destination channel ID
# Username-based sources are resolved at startup and added to this dict
# NOTE: Event handlers below do NOT filter on chats= at registration time.
# They look up CHANNEL_MAP live on every incoming event, so it's safe for
# resolve_new_channels() to populate this dict after handlers are registered.
CHANNEL_MAP = {
    -1001785197109: -1003891219488,  # AnabelSignals → BREY TRADING FX VIP
    -1001284268486: -1003891219488,  # EasyForexPips → BREY TRADING FX VIP
    # New channels (IDs resolved at startup from usernames below)
    # @Goldsignalz_fx
    # @Golldtradersunny2
    # @FX_Gold_killler
    # @ZAGoldScalper
    # @GBPUSDUSDJPYEURUSDSIGNALSfx (filtered gold only)
    # @BLUEMARKETFREEfx (filtered gold only)
}

# New channel usernames to resolve at startup
NEW_SOURCE_USERNAMES = [
    "Goldsignalz_fx",
    "Golldtradersunny2",
    "FX_Gold_killler",
    "ZAGoldScalper",
    "GBPUSDUSDJPYEURUSDSIGNALSfx",
    "BLUEMARKETFREEfx",
]

DESTINATION_ID = -1003891219488  # BREY TRADING FX VIP

# --- NAMES/WATERMARKS TO REMOVE ---
NAMES_TO_REMOVE = [
    r"Anabel\s*Signals?\s*",
    r"Anabel\s*",
    r"Easy\s*Forex\s*Pips?\s*",
    r"EasyForexPips?\s*",
    r"Easy\s*Forex\s*👑?\s*OFFICIAL\s*CHANNEL\s*",
    r"Easy\s*Forex\s*",
    r"Gold\s*Signal[sz]?\s*FX\s*",
    r"Goldsignalz_fx\s*",
    r"Goldsignalz\s*",
    r"Gold\s*Trader\s*Sunny\s*",
    r"Golldtradersunny\d*\s*",
    r"BLUE\s*MARKET\s*FREE\s*",
    r"BLUEMARKETFREEfx\s*",
    r"FX\s*Gold\s*Kill+er\s*",
    r"FX_Gold_killler\s*",
    r"ZA\s*Gold\s*Scalper\s*",
    r"ZAGoldScalper\s*",
    r"GBPUSD.*SIGNALS\s*fx\s*",
    r"GBPUSDUSDJPYEURUSDSIGNALSfx\s*",
    r"t\.me/\S+",
    r"@\w+",
]

# --- WORD REPLACEMENTS ---
WORD_REPLACEMENTS = {
    r"\bVENDER\b": "SELL",
    r"\bCOMPRAR\b": "BUY",
    r"\bVende\b": "SELL",
    r"\bCompra\b": "BUY",
    r"\bSELL\b": "SELL",
    r"\bBUY\b": "BUY",
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
    r"refer",
    r"invite",
    r"click here",
    r"follow us",
    r"our channel",
    r"nuestro canal",
    r"free trial",
    r"prueba gratis",
    r"discount",
    r"descuento",
]

# --- GOLD ONLY PATTERNS ---
GOLD_PATTERNS = [
    r"\bxauusd\b",
    r"\bxau/usd\b",
    r"\bxau\b",
    r"\bgold\b",
    r"\boro\b",
    r"\bxau\s*/\s*usd\b",
]

# --- VALID TRADING SIGNAL PATTERNS ---
ALLOWED_PATTERNS = [
    r"señal lista",
    r"signal ready",
    r"pendientes",
    r"\bvender\b",
    r"\bcomprar\b",
    r"\bsell\b",
    r"\bbuy\b",
    r"entrar entre",
    r"\bentry\b",
    r"\bentrada\b",
    r"\bxauusd\b",
    r"\bxau/usd\b",
    r"\bxau\b",
    r"\bgold\b",
    r"\boro\b",
    r"\bsl\b",
    r"stop loss",
    r"\btp1\b",
    r"\btp2\b",
    r"\btp3\b",
    r"\btp4\b",
    r"\btp\s*\d\b",
    r"take profit",
    r"\basegura\b",
    r"\bsecure\b",
    r"todo en break",
    r"break even",
    r"breakeven",
    r"break en",
    r"colocar break",
    r"coloquen break",
    r"place break",
    r"50%",
    r"\bganancias\b",
    r"\bprofit\b",
    r"\bpagando\b",
    r"\bdentro\b",
    r"\bseguimos\b",
    r"\bcierra\b",
    r"\bclose\b",
    r"razón para",
    r"\bpatrón\b",
    r"\bengulfing\b",
    r"\balcanzado\b",
    r"\binvalidada\b",
    r"\bretroceso\b",
    r"\bcorriendo\b",
    r"\banálisis\b",
    r"\btendencia\b",
    r"\bimpulso\b",
    r"\bsoporte\b",
    r"\bresistencia\b",
    r"super entrada",
    r"\bcolocar\b",
    r"\bcoloquen\b",
    r"\bpending\b",
    r"\bmarket\b",
    r"\blimit\b",
    r"\btarget\b",
    r"\brisk\b",
    r"\blot\b",
    r"\bpips?\b",
    r"\bscalp\b",
    r"price action",
    r"order block",
    r"support",
    r"resistance",
    r"liquidity",
    r"\bfib\b",
    r"fibonacci",
]

# Signal update patterns (these may not mention gold explicitly)
SIGNAL_UPDATE_PATTERNS = [
    r"\bbreak\b",
    r"\btp\s*\d\b",
    r"take profit",
    r"stop loss",
    r"\basegura\b",
    r"\bcierra\b",
    r"\bpagando\b",
    r"\bdentro\b",
    r"\balcanzado\b",
    r"\bcorriendo\b",
    r"señal lista",
    r"\bpendientes\b",
    r"\bseguimos\b",
    r"\binvalidada\b",
    r"\bprofit\b",
    r"\bclose\b",
    r"moved to",
    r"trailing",
    r"secured",
]

# --- SYSTEM SETTINGS ---
SETTINGS = {
    "ai_translate": True,
    "target_language": "es",   # Spanish by default
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
# STARTUP: Resolve new channel usernames → IDs
# -------------------------------------------------------------------
async def resolve_new_channels():
    """Resolve username-based source channels and add to CHANNEL_MAP.

    Handlers below check CHANNEL_MAP live on every event (no chats= filter
    at registration time), so it's safe to mutate this dict here, after
    handlers are already registered.
    """
    resolved = []
    failed = []
    for username in NEW_SOURCE_USERNAMES:
        try:
            entity = await user_client.get_entity(username)
            channel_id = entity.id
            # Telegram supergroup/channel IDs need -100 prefix
            full_id = int(f"-100{channel_id}")
            if full_id not in CHANNEL_MAP:
                CHANNEL_MAP[full_id] = DESTINATION_ID
                resolved.append(f"✅ @{username} → ID: {full_id}")
            else:
                resolved.append(f"ℹ️ @{username} already mapped")
        except Exception as e:
            failed.append(f"❌ @{username}: {e}")

    print("\n📡 Channel Resolution:")
    for r in resolved:
        print(f"  {r}")
    for f in failed:
        print(f"  {f}")
    print(f"\n📡 Total source channels: {len(CHANNEL_MAP)}")


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
    """Check if the message has no-forward protection enabled."""
    return getattr(message, 'noforwards', False)


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


def is_gold_signal(text):
    """Check if message is specifically about Gold/XAUUSD."""
    if not text:
        return False
    for pattern in GOLD_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def is_allowed_message(text):
    """Message must be a valid trading signal AND gold-related."""
    if not text:
        return False
    is_trading = any(
        re.search(p, text, re.IGNORECASE)
        for p in ALLOWED_PATTERNS
    )
    if not is_trading:
        return False
    # Must be gold or a signal update (TP hit, break even, etc.)
    is_update = any(
        re.search(p, text, re.IGNORECASE)
        for p in SIGNAL_UPDATE_PATTERNS
    )
    return is_gold_signal(text) or is_update


def is_promotional(text):
    """Detect promotional/spam content."""
    if not text:
        return False
    promo_patterns = [
        r"join (our|my|the)?\s*(free|vip|premium|channel)",
        r"click (the|this)?\s*link",
        r"subscribe",
        r"t\.me/\+",           # invite links
        r"joinchat",
        r"contact (us|me)",
        r"dm (us|me)",
        r"send (us|me)",
        r"reach out",
        r"telegram.*vip",
        r"vip.*telegram",
        r"free signals",
        r"señales gratis",
        r"canal gratis",
        r"únete",
        r"registro",
        r"register",
        r"website",
        r"whatsapp",
        r"instagram",
        r"facebook",
        r"youtube",
    ]
    for pattern in promo_patterns:
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
    """Clean watermarks, links, handles, and normalize text."""
    if not text:
        return text

    # Remove channel names / watermarks
    for pattern in NAMES_TO_REMOVE:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove all URLs and invite links
    text = re.sub(
        r'https?://\S+|t\.me/\S+|www\.\S+|joinchat/\S+',
        '', text
    )

    # Remove leftover @ handles
    text = re.sub(r'@\w+', '', text)

    # Apply standard word replacements
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Apply custom replacements
    for old, new in SETTINGS["custom_replacements"].items():
        text = re.sub(
            re.escape(old), new, text, flags=re.IGNORECASE
        )

    # Remove lines that are purely promotional after cleaning
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip empty-after-clean lines or pure punctuation/emoji remnants
        if stripped and not re.match(r'^[\s\-_•|/\\:]+$', stripped):
            cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

    # Collapse excess blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def translate_text(text):
    """Translate text to target language (default: Spanish)."""
    if not text or not SETTINGS["ai_translate"]:
        return text
    try:
        translated = GoogleTranslator(
            source='auto',
            target=SETTINGS["target_language"]
        ).translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"⚠️ Translation error: {e}")
        return text  # Return original if translation fails


def format_signal_professional(text):
    """
    Apply light formatting to make signals look clean and professional.
    Capitalizes key trading terms consistently.
    """
    if not text:
        return text

    # Ensure BUY/SELL are uppercase
    text = re.sub(r'\bBUY\b', 'BUY', text, flags=re.IGNORECASE)
    text = re.sub(r'\bSELL\b', 'SELL', text, flags=re.IGNORECASE)

    # Ensure XAUUSD is uppercase
    text = re.sub(r'\bxauusd\b', 'XAUUSD', text, flags=re.IGNORECASE)
    text = re.sub(r'\bxau/usd\b', 'XAU/USD', text, flags=re.IGNORECASE)

    # Ensure TP/SL labels are uppercase
    text = re.sub(r'\btp(\d)\b', r'TP\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsl\b', 'SL', text, flags=re.IGNORECASE)

    return text


def process_message(raw_text):
    """Full pipeline: clean → translate → format → sign."""
    if not raw_text:
        return None
    text = clean_message(raw_text)
    if not text:
        return None
    text = translate_text(text)
    if not text:
        return None
    text = format_signal_professional(text)
    text = text + SIGNATURE
    return text


# -------------------------------------------------------------------
# MENU HELPERS
# -------------------------------------------------------------------
def get_language_buttons():
    buttons = []
    row = []
    for lang_name, lang_code in LANGUAGES.items():
        current = "✅ " if lang_code == SETTINGS["target_language"] else ""
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
    translate_status = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
    pause_label = "▶️ Resume" if SETTINGS["paused"] else "⏸ Pause"
    lang_name = next(
        (k for k, v in LANGUAGES.items()
         if v == SETTINGS["target_language"]),
        SETTINGS["target_language"]
    )
    return [
        [Button.inline(
            f"🌐 Translation: {translate_status}", "toggle_translate"
        )],
        [Button.inline(
            f"🗣 Language: {lang_name}", "change_language"
        )],
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
            "👋 **Bienvenido a Brey Trading Signal Bot!**\n\n"
            "🥇 Copio señales de **Gold (XAUUSD)** únicamente\n"
            "📡 Fuentes: Goldsignalz FX, Gold Trader Sunny, "
            "FX Gold Killer, ZA Gold Scalper,\n"
            "      AnabelSignals, EasyForexPips, "
            "y más canales de oro\n"
            "➡️ Destino: **BREY TRADING FX VIP**\n\n"
            "🌐 Idioma predeterminado: **Español**\n\n"
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
            "📋 **Comandos Disponibles:**\n\n"
            "**🔧 Sistema:**\n"
            "➡️ `/start` - Bienvenida + menú\n"
            "➡️ `/menu` - Panel de control\n"
            "➡️ `/help` - Todos los comandos\n"
            "➡️ `/status` - Estado actual\n"
            "➡️ `/channels` - Canales configurados\n\n"
            "**⏯ Control:**\n"
            "➡️ `/pause` - Pausar bot\n"
            "➡️ `/resume` - Reanudar bot\n\n"
            "**🌐 Traducción:**\n"
            "➡️ `/ai on` - Activar traducción\n"
            "➡️ `/ai off` - Desactivar traducción\n"
            "➡️ `/language es` - Español\n"
            "➡️ `/language en` - Inglés\n"
            "➡️ `/language fr` - Francés\n\n"
            "**✏️ Palabras:**\n"
            "➡️ `/addword vieja:nueva` - Reemplazar palabra\n"
            "➡️ `/removeword palabra` - Quitar reemplazo\n"
            "➡️ `/wordlist` - Ver reemplazos\n"
            "➡️ `/blockword palabra` - Bloquear palabra\n"
            "➡️ `/unblockword palabra` - Desbloquear\n"
            "➡️ `/blocklist` - Ver bloqueadas\n"
        )

    elif command == "/status":
        paused = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        translate = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.respond(
            f"📊 **Estado del Sistema:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `{translate}`\n"
            f"• Idioma: `{lang_name}`\n"
            f"• Solo Gold/XAUUSD: `✅ Activado`\n"
            f"• Canales fuente: `{len(CHANNEL_MAP)}`\n"
            f"• Reemplazos personalizados: "
            f"`{len(SETTINGS['custom_replacements'])}`\n"
            f"• Palabras bloqueadas: "
            f"`{len(SETTINGS['blocked_words'])}`\n"
        )

    elif command == "/pause":
        SETTINGS["paused"] = True
        await event.respond("⏸ **Bot Pausado.**")

    elif command == "/resume":
        SETTINGS["paused"] = False
        await event.respond("▶️ **Bot Reanudado.**")

    elif command.startswith("/ai "):
        mode = command.split("/ai ")[1].strip()
        if mode == "on":
            SETTINGS["ai_translate"] = True
            lang_name = next(
                (k for k, v in LANGUAGES.items()
                 if v == SETTINGS["target_language"]),
                SETTINGS["target_language"]
            )
            await event.respond(
                f"✅ **Traducción ACTIVADA** → `{lang_name}`"
            )
        elif mode == "off":
            SETTINGS["ai_translate"] = False
            await event.respond("🛑 **Traducción DESACTIVADA.**")

    elif command.startswith("/language "):
        lang = command.split("/language ")[1].strip()
        if lang in LANGUAGES.values():
            SETTINGS["target_language"] = lang
            lang_name = next(
                (k for k, v in LANGUAGES.items() if v == lang), lang
            )
            await event.respond(f"🌐 **Idioma: {lang_name}**")
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
                    "❌ Usa: `/addword palabravieja:palabranueva`"
                )
        except Exception:
            await event.respond(
                "❌ Usa: `/addword palabravieja:palabranueva`"
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
                 for k, v in SETTINGS["custom_replacements"].items()]
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
            await event.respond(f"⚠️ Ya estaba bloqueado.")

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
            await event.respond(f"🚫 **Bloqueadas:**\n\n{words}")
        else:
            await event.respond("✅ Ninguna bloqueada.")

    elif command == "/channels":
        await event.respond(
            "📡 **Canales Fuente:**\n\n"
            "• @Goldsignalz\\_fx\n"
            "• @Golldtradersunny2\n"
            "• @FX\\_Gold\\_killler\n"
            "• @ZAGoldScalper\n"
            "• @GBPUSDUSDJPYEURUSDSIGNALSfx\n"
            "• @BLUEMARKETFREEfx\n"
            "• @AnabelSignals\n"
            "• @EasyForexPips\n\n"
            f"**Destino:** BREY TRADING FX VIP\n"
            f"**Canales mapeados en memoria:** {len(CHANNEL_MAP)}\n\n"
            "🥇 Solo señales de Gold (XAUUSD)"
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
        status = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        await event.answer(f"Traducción: {status}")
        await event.edit(
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "change_language":
        await event.edit(
            "🌐 **Selecciona el idioma de las señales:**",
            buttons=get_language_buttons()
        )

    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        SETTINGS["target_language"] = lang_code
        lang_name = next(
            (k for k, v in LANGUAGES.items() if v == lang_code),
            lang_code
        )
        await event.answer(f"✅ {lang_name}")
        await event.edit(
            f"✅ **Idioma: {lang_name}**",
            buttons=get_language_buttons()
        )

    elif data == "toggle_pause":
        SETTINGS["paused"] = not SETTINGS["paused"]
        status = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        await event.answer(f"Bot: {status}")
        await event.edit(
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "show_status":
        paused = "⏸ PAUSADO" if SETTINGS["paused"] else "▶️ ACTIVO"
        translate = "✅ ON" if SETTINGS["ai_translate"] else "🛑 OFF"
        lang_name = next(
            (k for k, v in LANGUAGES.items()
             if v == SETTINGS["target_language"]),
            SETTINGS["target_language"]
        )
        await event.answer("Estado!")
        await event.edit(
            f"📊 **Estado:**\n\n"
            f"• Estado: `{paused}`\n"
            f"• Traducción: `{translate}`\n"
            f"• Idioma: `{lang_name}`\n"
            f"• Solo Gold: `✅ ON`\n"
            f"• Canales fuente: `{len(CHANNEL_MAP)}`",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "show_channels":
        await event.answer("Canales!")
        await event.edit(
            "📡 **Canales Fuente → BREY TRADING FX VIP:**\n\n"
            "• @Goldsignalz\\_fx\n"
            "• @Golldtradersunny2\n"
            "• @FX\\_Gold\\_killler\n"
            "• @ZAGoldScalper\n"
            "• @GBPUSDUSDJPYEURUSDSIGNALSfx\n"
            "• @BLUEMARKETFREEfx\n"
            "• @AnabelSignals\n"
            "• @EasyForexPips\n\n"
            "🥇 Solo señales de Gold/XAUUSD",
            buttons=[[Button.inline("🔙 Volver", "back_menu")]]
        )

    elif data == "back_menu":
        await event.edit(
            "🎛 **Panel de Control:**",
            buttons=get_main_menu_buttons()
        )

    elif data == "close":
        await event.delete()


# -------------------------------------------------------------------
# ALBUM HANDLER (multiple photos sent together)
# -------------------------------------------------------------------
# NOTE: no chats= filter here — CHANNEL_MAP is checked live inside the
# handler so newly-resolved username channels work without a restart.
@user_client.on(events.Album())
async def album_handler(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    # Skip audio/video albums
    for msg in event.messages:
        if is_audio_message(msg) or is_video_message(msg):
            print("⏭️ Skipped album: contains audio/video")
            return

    # Check noforwards flag on any message in the album
    for msg in event.messages:
        if is_noforwards(msg):
            print("⏭️ Skipped album: noforwards protection")
            return

    # Find and validate caption
    caption = None
    has_valid_caption = False
    for msg in event.messages:
        if msg.message:
            raw = msg.message
            if is_blocked_image(raw):
                print("⏭️ Skipped album: blocked image phrase")
                return
            if is_promotional(raw):
                print("⏭️ Skipped album: promotional content")
                return
            if is_blocked_word_found(raw):
                print("⏭️ Skipped album: blocked word")
                return
            if is_allowed_message(raw):
                has_valid_caption = True
                caption = process_message(raw)
                break

    if not has_valid_caption:
        print("⏭️ Skipped album: not a gold signal")
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
            print(f"✅ Gold album → {destination_id}")
        except Exception as e:
            print(f"❌ Album send failed: {e}")


# -------------------------------------------------------------------
# SINGLE MESSAGE HANDLER
# -------------------------------------------------------------------
# NOTE: no chats= filter here either, for the same reason as above.
@user_client.on(events.NewMessage())
async def replication_engine(event):
    if SETTINGS["paused"]:
        return

    source_id = event.chat_id
    destination_id = CHANNEL_MAP.get(source_id)
    if not destination_id:
        return

    # Skip grouped messages (handled by album_handler)
    if event.message.grouped_id:
        return

    # Skip noforwards-protected messages
    if is_noforwards(event.message):
        print("⏭️ Skipped: noforwards protection")
        return

    # Skip audio and video
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

    # --- PHOTO WITH CAPTION ---
    if is_photo:
        if not raw_text:
            print("⏭️ Skipped: photo with no caption")
            return
        if is_blocked_image(raw_text):
            print("⏭️ Skipped: blocked image phrase")
            return
        if is_promotional(raw_text):
            print("⏭️ Skipped: promotional photo")
            return
        if not is_allowed_message(raw_text):
            print("⏭️ Skipped: photo not a gold signal")
            return

    # --- TEXT ONLY ---
    if not has_media:
        if not raw_text:
            return
        if not is_allowed_message(raw_text):
            print("⏭️ Skipped: not a gold signal")
            return
        if has_links(raw_text):
            print("⏭️ Skipped: contains links")
            return
        if is_promotional(raw_text):
            print("⏭️ Skipped: promotional content")
            return
        if is_blocked_word_found(raw_text):
            print("⏭️ Skipped: blocked word")
            return

    # --- PROCESS & SEND ---
    final_text = process_message(raw_text) if raw_text else None

    try:
        if is_photo:
            # send_file is more reliable than send_message(file=...) for
            # media + caption together.
            await user_client.send_file(
                destination_id,
                event.message.media,
                caption=final_text
            )
        else:
            await user_client.send_message(
                destination_id,
                final_text
            )
        print(f"✅ Gold signal: {source_id} → {destination_id}")
    except Exception as delivery_error:
        print(f"❌ Delivery failed: {delivery_error}")


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
async def main():
    await user_client.connect()
    if not await user_client.is_user_authorized():
        print("❌ ERROR: Session string invalid or expired!")
        return
    print("✅ Userbot (scraper) connected.")

    # Resolve new channel usernames to IDs.
    # Handlers are already registered at this point (decorators ran at
    # import time), but since they check CHANNEL_MAP live instead of
    # filtering on chats= at registration, this works correctly.
    await resolve_new_channels()

    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Bot control panel connected.")

    print("\n🚀 Brey Trading Signal Bot RUNNING!")
    print("🥇 Gold (XAUUSD) signals only")
    print("🌐 Default language: Español (Spanish)")
    print(f"📡 Monitoring {len(CHANNEL_MAP)} source channels\n")

    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )


asyncio.run(main())

