"""Collega il Dr.Scount Bot Offerte al bot: menu Telegram, ricerca periodica, pubblicazione sul canale."""
from __future__ import annotations

import datetime as dt
import html
import os
import time
from pathlib import Path

import telegram_bot as bot

from . import engine, menu, settings
from .categories import CATEGORIES
from .client import CreatorsClient
from .image import download, render_deal

OUT = Path(__file__).resolve().parent.parent.parent / "deals_tmp"


def enabled() -> bool:
    return bool(os.getenv("CREATORS_CLIENT_ID") and os.getenv("CREATORS_CLIENT_SECRET"))


SHARE = ("https://t.me/share/url?url=https://t.me/DRSCOUNT&text=Ciao%20ho%20trovato%20questo%20canale%20che%20posta%20"
         "ogni%20giorno%20le%20migliori%20offerte%20del%20web%0AEntra%20e%20clicca%20su%20unisciti%20anche%20tu%20%E2%98%BA%EF%B8%8F")


def caption(d: engine.Deal) -> str:
    """Stesso stile del canale @DRSCOUNT: titolo, prezzo con ✅/❌, link, recensioni, condividi."""
    parts = [html.escape(d.full_title or d.title)]
    if d.historic_low:
        parts.append("📉 <b>MINIMO STORICO!</b>")
    parts.append(f"💰 Al prezzo di ✅<b>{d.price_txt}</b> invece di ❌<s>{d.old_price_txt}</s> (<b>{d.discount}%</b>)")
    parts.append(f'🛒 Clicca qui per acquistare <a href="{d.link}">{d.link}</a>')
    if d.reviews:
        parts.append(f"⭐️ {d.reviews:,} Recensioni: {d.rating:.1f} / 5.0".replace(",", "."))
    parts.append(f'Condividi <a href="{html.escape(SHARE)}">@DRSCOUNT</a>')
    return "\n\n".join(parts)


def _save_cfg(s: dict, cfg: dict):
    s["settings"] = {k: v for k, v in cfg.items() if not k.startswith("_")}


def handle_menu(s: dict) -> bool:
    """Risponde a /impostazioni e ai pulsanti del menu. Ritorna True se qualcosa è cambiato."""
    changed = False
    while bot.menu_events:
        kind, obj = bot.menu_events.pop(0)
        cfg = settings.load(s)
        if kind == "menu":
            bot.send_menu(*menu.render("main", cfg))
            continue
        page = menu.apply(kind[4:], cfg)
        if kind == "cfg:noop":
            bot.ack(obj, "")
            continue
        if cfg.pop("_now", False):
            s["deals_force"] = True
        _save_cfg(s, cfg)
        bot.ack(obj, "🔎 Cerco…" if s.get("deals_force") else "✅ Salvato")
        bot.edit_menu(obj["message"]["message_id"], *menu.render(page, cfg))
        changed = True
    return changed


def step(s: dict, client: CreatorsClient | None = None) -> bool:
    """Un giro di ricerca + pubblicazione. Ritorna True se ha pubblicato qualcosa."""
    cfg = settings.load(s)
    force = s.pop("deals_force", False)
    if not enabled() or not cfg["attivo"]:
        return False
    now = time.time()
    if not force and now - s.get("deals_last_scan", 0) < cfg["ogni_minuti"] * 60:
        return False
    s["deals_last_scan"] = now
    client = client or CreatorsClient()
    found = engine.scan(client, cfg, s)
    chosen = engine.pick(found, cfg, s, limit=cfg["max_per_giro"] if not force else max(cfg["max_per_giro"], 3))
    posted = 0
    for d in chosen:
        try:
            path = render_deal(download(d.photo_url), d.title, d.price_txt, d.old_price_txt, d.discount,
                               CATEGORIES[d.category]["label"], OUT / f"{d.asin}.jpg", d.basis == "WAS_PRICE")
            bot.send_deal(cfg["canale"], path, caption(d), d.link)
        except Exception as e:
            print(f"[bot-offerte] {d.asin}: {e}")
            continue
        day = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).strftime("%Y-%m-%d")
        s.setdefault("deals_titles", {})[engine.title_key(d)] = dt.datetime.now(dt.timezone.utc).isoformat()
        s.setdefault("deals_seen", {})[d.asin] = dt.datetime.now(dt.timezone.utc).isoformat()
        daily = s.setdefault("deals_daily", {})
        daily.setdefault(day, {})
        daily[day][d.category] = daily[day].get(d.category, 0) + 1
        posted += 1
    for old in sorted(s.get("deals_daily", {}))[:-3]:   # tiene solo gli ultimi giorni
        s["deals_daily"].pop(old, None)
    # storico prezzi nostro: servirà per riconoscere i veri sconti e i minimi storici
    hist = s.setdefault("deals_prices", {})
    for d in found:
        hist.setdefault(d.asin, []).append([dt.date.today().isoformat(), d.price])
        hist[d.asin] = hist[d.asin][-30:]
    if len(hist) > 600:
        for k in list(hist)[:len(hist) - 600]:
            hist.pop(k)
    if force:
        bot.notify(f"🔎 Ricerca fatta: {len(found)} offerte valide, {posted} pubblicate sul canale.")
    return posted > 0
