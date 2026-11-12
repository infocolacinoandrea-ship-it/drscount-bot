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
from render import render_post, render_story

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # per importare il generatore dei reel (cartella reel/)
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


def image_url(post_id, suffix: str = "") -> str:
    return f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/posts/{post_id}{suffix}.jpg"


def publish_story(pid) -> str:
    """Pubblica la storia del post (la crea se manca). Ritorna un testo per la notifica."""
    story = POSTS / f"{pid}_story.jpg"
    try:
        if not story.exists():
            render_story(POSTS / f"{pid}.jpg", story)
            push_changes("bot: storia")
            time.sleep(8)  # lascia a GitHub il tempo di rendere disponibile l'immagine
        instagram.publish_image(image_url(pid, "_story"), story=True)
        return "\n📲 Storia pubblicata"
    except Exception as e:
        return f"\n⚠️ Storia non pubblicata: {e}"


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


def publish_now(s: dict, pid, caption: str) -> str:
    """Pubblica post (+ storia) e ritorna il testo per la notifica. Solleva eccezione se il post fallisce."""
    media_id = instagram.publish_image(image_url(pid), cap.normalize(caption))
    s["published"][str(pid)] = media_id
    s["last_post"] = dt.datetime.now(dt.timezone.utc).isoformat()
    link = instagram.permalink(media_id)
    extra = ""
    if config.AUTO_STORY:
        extra = publish_story(pid) if instagram.publishing_room() > 1 else "\n⏸️ Storia saltata: limite giornaliero di Instagram"
    return f"✅ Pubblicato su Instagram {link}".strip() + extra


MEDIA_BRANCH = "media"


def push_media(files: list[Path]) -> str:
    """Carica i video sul ramo 'media' del repo, che contiene solo l'ultimo reel
    (viene sovrascritto ogni volta, così il repository non si gonfia). Ritorna l'URL base."""
    def git(*a, inp=None):
        return subprocess.run(["git", *a], cwd=ROOT, check=True, capture_output=True,
                              text=True, input=inp).stdout.strip()
    entries = "".join(f"100644 blob {git('hash-object', '-w', str(f))}\t{f.name}\n" for f in files)
    tree = git("mktree", inp=entries)
    commit = git("commit-tree", tree, "-m", "media: reel")
    git("push", "-q", "-f", "origin", f"{commit}:refs/heads/{MEDIA_BRANCH}")
    return f"https://raw.githubusercontent.com/{config.REPO}/{MEDIA_BRANCH}/"


def make_reel(o: scraper.Offer) -> tuple[Path, Path]:
    from reel.render_reel import render_reel
    img = Image.open(io.BytesIO(scraper.download(o.photo_url)))
    tmp = ROOT / "reels_tmp"
    video, cover = tmp / f"{o.post_id}_reel.mp4", tmp / f"{o.post_id}_reel.jpg"
    render_reel(img, o.short_title, o.price, o.old_price, o.discount, o.historic_low,
                video, cover_path=cover)
    return video, cover


def publish_reel_now(s: dict, o: scraper.Offer, caption: str) -> str:
    """Genera e pubblica il reel + la storia con lo stesso video."""
    video, cover = make_reel(o)
    base = push_media([video, cover])
    time.sleep(10)  # lascia a GitHub il tempo di rendere disponibili i file
    media_id = instagram.publish_video(base + video.name, cap.normalize(caption), cover_url=base + cover.name)
    s["published"][str(o.post_id)] = media_id
    s["last_post"] = dt.datetime.now(dt.timezone.utc).isoformat()
    link = instagram.permalink(media_id)
    extra = ""
    if config.AUTO_STORY:
        if instagram.publishing_room() > 1:
            try:
                instagram.publish_video(base + video.name, story=True)
                extra = "\n📲 Storia (video) pubblicata"
            except Exception as e:
                extra = f"\n⚠️ Storia non pubblicata: {e}"
        else:
            extra = "\n⏸️ Storia saltata: limite giornaliero di Instagram"
    return f"🎬 Reel pubblicato su Instagram {link}".strip() + extra


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
            msg = publish_now(s, pid, p["caption"])
            bot.mark(p["message_id"], "✅ Pubblicato")
            bot.notify(msg)
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
    render_story(out, POSTS / f"{o.post_id}_story.jpg")
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


def auto_publish(s: dict) -> bool:
    """Pubblica direttamente la migliore offerta nuova, una alla volta e distanziate."""
    last = s.get("last_post")
    if last and dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last) < dt.timedelta(
            minutes=config.MIN_MINUTES_BETWEEN_POSTS):
        return False
    if instagram.publishing_room() < 1:
        return False
    today = dt.date.today().isoformat()
    for o in pick_offers(s)[:1]:
        s["seen"].append(o.post_id)
        try:
            text = cap.build_caption(o)
            msg = None
            # Alternanza: un'offerta come reel + storia, la successiva come post + storia
            if config.REELS and s.get("next_format", "reel") == "reel":
                save_state(s)
                try:
                    msg = publish_reel_now(s, o, text)
                    s["next_format"] = "post"
                except Exception as e:
                    print(f"Reel non riuscito per {o.post_id}: {e}", file=sys.stderr)
                    bot.notify(f"⚠️ Reel non riuscito ({e}), pubblico come post")
            if msg is None:
                path, text = make_post(o)
                save_state(s)
                push_changes("bot: nuovo post")
                time.sleep(10)  # lascia a GitHub il tempo di rendere disponibile l'immagine
                msg = publish_now(s, o.post_id, text)
                s["next_format"] = "reel"
            s["daily"][today] = s["daily"].get(today, 0) + 1
            bot.notify(f"{msg}\n🛒 {o.short_title} a {o.price} (-{o.discount}%)")
            return True
        except Exception as e:
            print(f"Pubblicazione automatica non riuscita per {o.post_id}: {e}", file=sys.stderr)
            bot.notify(f"⚠️ Non sono riuscito a pubblicare {o.short_title}: {e}")
            return True
    return False


def send_new_previews(s: dict) -> bool:
    if config.AUTO_PUBLISH:
        return auto_publish(s)
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


def seconds_until_active() -> float:
    now = dt.datetime.now(ZoneInfo("Europe/Rome"))
    start = now.replace(hour=config.ACTIVE_HOURS[0], minute=0, second=0, microsecond=0)
    if now >= start:
        start += dt.timedelta(days=1)
    return (start - now).total_seconds()


def run():
    if not active_now():
        # Di notte non pubblica: aspetta (al massimo un giro) e poi il workflow si rilancia da solo,
        # così la mattina il bot è già acceso alle 7 senza dipendere dai controlli programmati di GitHub.
        if config.LISTEN_MINUTES:
            time.sleep(min(config.LISTEN_MINUTES * 60, seconds_until_active() + 5))
        return
    s = load_state()
    try:
        try:
            handle_decisions(s)
            expire_pending(s)
            send_new_previews(s)
            maybe_refresh_token(s)
        except Exception as e:  # un intoppo di rete non deve fermare il bot
            print(f"errore nel primo controllo: {e}", file=sys.stderr)
        save_state(s)
        push_changes()
        if not config.LISTEN_MINUTES:
            return
        # Modalità ascolto: risponde ai pulsanti in pochi secondi
        end = time.time() + config.LISTEN_MINUTES * 60
        next_check = time.time() + config.CHECK_OFFERS_EVERY_MIN * 60
        while time.time() < end - 60 and active_now():
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
