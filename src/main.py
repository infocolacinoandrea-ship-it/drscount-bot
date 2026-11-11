"""Un giro del sistema. Viene lanciato ogni 15 minuti da GitHub Actions.

1. Legge i tuoi ✅/❌ sul bot e pubblica su Instagram i post approvati.
2. Legge il canale, sceglie le offerte migliori nuove, crea l'immagine
   e ti manda l'anteprima sul bot.

Uso locale per provare la grafica senza inviare niente:
    python src/main.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import subprocess
import sys
import time
import traceback
from zoneinfo import ZoneInfo
from pathlib import Path

from PIL import Image

import caption as cap
import config
import instagram
import scoring
import scraper
import telegram_bot as bot
from render import render_post

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state.json"
POSTS = ROOT / "posts"


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"seen": [], "pending": {}, "published": {}, "tg_offset": 0, "daily": {}, "last_refresh": ""}


def save_state(s: dict):
    s["seen"] = s["seen"][-1000:]
    s["daily"] = dict(sorted(s["daily"].items())[-14:])
    STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False))


def image_url(post_id: int) -> str:
    return f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/posts/{post_id}.jpg"


def push_changes(msg: str = "bot: aggiornamento"):
    """Salva su GitHub immagini e stato, così Instagram può scaricare subito le immagini."""
    if not config.REPO:
        return
    try:
        subprocess.run(["git", "add", "state.json", "posts"], cwd=ROOT, check=False, capture_output=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT, check=True)
        subprocess.run(["git", "pull", "-q", "--rebase", "-X", "theirs"], cwd=ROOT, check=False)
        subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
    except Exception as e:
        print(f"push non riuscito: {e}", file=sys.stderr)


def handle_decisions(s: dict, wait: int = 0) -> bool:
    decisions, s["tg_offset"] = bot.get_decisions(s["tg_offset"], wait)
    for action, pid, cq in decisions:
        p = s["pending"].pop(str(pid), None)
        if not p:
            bot.ack(cq, "Già gestito")
            continue
        if action == "no":
            bot.ack(cq, "Scartato")
            bot.mark(p["message_id"], "❌ Scartato")
            continue
        bot.ack(cq, "Pubblico su Instagram…")
        try:
            media_id = instagram.publish_image(image_url(pid), cap.normalize(p["caption"]))
            s["published"][str(pid)] = media_id
            link = instagram.permalink(media_id)
            bot.mark(p["message_id"], "✅ Pubblicato")
            bot.notify(f"✅ Pubblicato su Instagram {link}".strip())
        except Exception as e:
            s["pending"][str(pid)] = p  # riprova al prossimo ✅
            bot.notify(f"⚠️ Pubblicazione non riuscita: {e}")
            # rimette i pulsanti per poter riprovare
            bot._api("editMessageReplyMarkup", data={
                "chat_id": config.ADMIN_CHAT_ID, "message_id": p["message_id"],
                "reply_markup": json.dumps({"inline_keyboard": [[
                    {"text": "✅ Riprova", "callback_data": f"ok:{pid}"},
                    {"text": "❌ Scarta", "callback_data": f"no:{pid}"}]]})})
    return bool(decisions)


def expire_pending(s: dict):
    """Le anteprime non approvate entro 36 ore scadono: il prezzo potrebbe essere cambiato."""
    now = dt.datetime.now(dt.timezone.utc)
    for pid, p in list(s["pending"].items()):
        if now - dt.datetime.fromisoformat(p["created"]) > dt.timedelta(hours=36):
            s["pending"].pop(pid)
            bot.mark(p["message_id"], "⌛ Scaduto")


def pick_offers(s: dict) -> list[scraper.Offer]:
    offers = scraper.fetch_offers(config.CHANNEL)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=config.LOOKBACK_HOURS)
    seen = set(s["seen"])
    fresh = [o for o in offers
             if o.post_id not in seen and o.date and dt.datetime.fromisoformat(o.date) >= since
             and scoring.eligible(o)]
    fresh.sort(key=scoring.score, reverse=True)
    today = dt.date.today().isoformat()
    room = config.MAX_PREVIEWS_PER_DAY - s["daily"].get(today, 0)
    return fresh[: max(0, min(config.MAX_PREVIEWS_PER_RUN, room))]


def make_post(o: scraper.Offer) -> tuple[Path, str]:
    img = Image.open(io.BytesIO(scraper.download(o.photo_url)))
    out = render_post(img, o.short_title, o.price, o.old_price, o.discount, o.historic_low,
                      POSTS / f"{o.post_id}.jpg")
    return out, cap.build_caption(o)


def maybe_refresh_token(s: dict):
    if not config.IG_TOKEN_EXPIRES:
        return  # token che non scade: niente da rinnovare
    today = dt.date.today()
    last = dt.date.fromisoformat(s["last_refresh"]) if s["last_refresh"] else None
    if last and (today - last).days < 7:
        return
    try:
        res = instagram.refresh_token()
        s["last_refresh"] = today.isoformat()
        if res.get("access_token") and res["access_token"] != config.IG_TOKEN:
            bot.notify("🔑 Instagram ha generato un nuovo token: aggiorna il secret IG_ACCESS_TOKEN "
                       "su GitHub con questo valore:\n\n" + res["access_token"])
    except Exception as e:
        bot.notify(f"⚠️ Non riesco a rinnovare il token Instagram: {e}")


def send_new_previews(s: dict) -> bool:
    today = dt.date.today().isoformat()
    sent = False
    for o in pick_offers(s):
        s["seen"].append(o.post_id)
        try:
            path, text = make_post(o)
        except Exception as e:
            print(f"Salto {o.post_id}: {e}", file=sys.stderr)
            continue
        mid = bot.send_preview(path, text, o.post_id)
        s["pending"][str(o.post_id)] = {
            "message_id": mid, "caption": text,
            "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        s["daily"][today] = s["daily"].get(today, 0) + 1
        sent = True
    return sent


def active_now() -> bool:
    h = dt.datetime.now(ZoneInfo("Europe/Rome")).hour
    return config.ACTIVE_HOURS[0] <= h < config.ACTIVE_HOURS[1]


def run():
    s = load_state()
    try:
        handle_decisions(s)
        expire_pending(s)
        send_new_previews(s)
        maybe_refresh_token(s)
        save_state(s)
        push_changes()
        if not config.LISTEN_MINUTES or not active_now():
            return
        # Modalità ascolto: risponde ai pulsanti in pochi secondi
        end = time.time() + config.LISTEN_MINUTES * 60
        next_check = time.time() + config.CHECK_OFFERS_EVERY_MIN * 60
        while time.time() < end - 60:
            try:
                changed = handle_decisions(s, wait=50)
                if time.time() >= next_check:
                    next_check = time.time() + config.CHECK_OFFERS_EVERY_MIN * 60
                    expire_pending(s)
                    changed = send_new_previews(s) or changed
                if changed:
                    save_state(s)
                    push_changes()
            except Exception as e:  # un errore di rete non deve fermare l'ascolto
                print(f"errore nel ciclo di ascolto: {e}", file=sys.stderr)
                time.sleep(10)
    finally:
        save_state(s)


def dry_run():
    offers = scraper.fetch_offers(config.CHANNEL)
    best = sorted([o for o in offers if scoring.eligible(o)], key=scoring.score, reverse=True)[:5]
    for o in best:
        path, text = make_post(o)
        print(f"[{scoring.score(o):.0f}] {o.short_title} -> {path}\n{text}\n{'-' * 40}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        dry_run() if args.dry_run else run()
    except Exception:
        traceback.print_exc()
        if config.BOT_TOKEN and config.ADMIN_CHAT_ID and not args.dry_run:
            try:
                bot.notify("⚠️ Dr.Scount bot: errore\n" + traceback.format_exc()[-800:])
            except Exception:
                pass
        sys.exit(1)
