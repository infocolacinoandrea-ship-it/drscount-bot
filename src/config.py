"""Impostazioni. I valori segreti arrivano dalle variabili d'ambiente (GitHub Secrets)."""
import os

# --- Canale sorgente ---
CHANNEL = os.getenv("TG_CHANNEL", "drscount")

# --- Bot Telegram per le approvazioni ---
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("TG_ADMIN_CHAT_ID", "")  # la tua chat con il bot

# --- Instagram (API con accesso Instagram) ---
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
# Token che iniziano con "EAA" (app Meta con accesso unificato) usano graph.facebook.com
# e non scadono; quelli con accesso Instagram ("IG...") usano graph.instagram.com.
IG_API = os.getenv("IG_API") or (
    "https://graph.facebook.com/v25.0" if IG_TOKEN.startswith("EAA") else "https://graph.instagram.com/v21.0")
IG_TOKEN_EXPIRES = not IG_TOKEN.startswith("EAA")

# --- Dove sono pubblicate le immagini (repo GitHub pubblico) ---
REPO = os.getenv("GITHUB_REPOSITORY", "")
BRANCH = os.getenv("GITHUB_REF_NAME", "main")

# --- Regole per scegliere le offerte "belle" ---
MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "40"))   # sconto minimo in %
MIN_RATING = float(os.getenv("MIN_RATING", "4.0"))    # stelle minime
MIN_REVIEWS = int(os.getenv("MIN_REVIEWS", "50"))     # recensioni minime
MAX_PREVIEWS_PER_RUN = int(os.getenv("MAX_PREVIEWS_PER_RUN", "2"))
MAX_PREVIEWS_PER_DAY = int(os.getenv("MAX_PREVIEWS_PER_DAY", "8"))
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "12"))

# Modalità ascolto: ogni giro resta acceso e reagisce subito ai tuoi ✅
LISTEN_MINUTES = int(os.getenv("LISTEN_MINUTES", "0"))   # 0 = giro veloce e basta
CHECK_OFFERS_EVERY_MIN = int(os.getenv("CHECK_OFFERS_EVERY_MIN", "10"))
ACTIVE_HOURS = (7, 23)  # ora italiana in cui il bot lavora

# Dopo ogni post pubblica anche una storia con la stessa grafica
AUTO_STORY = os.getenv("AUTO_STORY", "1") == "1"

# Pubblicazione automatica senza approvazione (1 = sì)
AUTO_PUBLISH = os.getenv("AUTO_PUBLISH", "0") == "1"
# Minuti minimi tra un post e l'altro, per non pubblicare a raffica
MIN_MINUTES_BETWEEN_POSTS = int(os.getenv("MIN_MINUTES_BETWEEN_POSTS", "20"))

# Parole che fanno salire il punteggio: il focus della pagina è la casa
HOME_KEYWORDS = [
    "casa", "cucina", "aspirapolvere", "robot", "friggitrice", "pentol", "padell",
    "lampad", "luce", "led", "bagno", "doccia", "asciugaman", "letto", "cuscin",
    "lenzuol", "piumon", "materasso", "organizer", "contenitor", "scaffal", "mensol",
    "pulizia", "detersiv", "lavatrice", "lavastoviglie", "ferro da stiro", "vaporiera",
    "macchina caffè", "caffè", "bollitore", "frullatore", "tostapane", "forno",
    "microonde", "termo", "stufa", "deumidificatore", "purificatore", "ventilatore",
    "tappeto", "tenda", "giardino", "attrezz", "trapano", "avvitatore", "arredo",
]
