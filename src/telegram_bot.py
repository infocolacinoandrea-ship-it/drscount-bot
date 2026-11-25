"""Bot Telegram: ti manda le anteprime e legge i tuoi ✅ / ❌."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

import config


def _api(method: str, **kwargs):
    # riprova fino a 4 volte se la connessione cade per un attimo
    for attempt in range(4):
        try:
            r = requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}", timeout=90, **kwargs)
            break
        except requests.exceptions.RequestException:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
            for f in (kwargs.get("files") or {}).values():
                f.seek(0)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method}: {data}")
    return data["result"]


def send_preview(image: Path, caption: str, post_id: int) -> int:
    kb = {"inline_keyboard": [[
        {"text": "✅ Pubblica", "callback_data": f"ok:{post_id}"},
        {"text": "❌ Scarta", "callback_data": f"no:{post_id}"},
    ]]}
    with open(image, "rb") as f:
        msg = _api(
            "sendPhoto",
            data={"chat_id": config.ADMIN_CHAT_ID, "caption": caption[:1024],
                  "reply_markup": json.dumps(kb)},
            files={"photo": f},
        )
    return msg["message_id"]


menu_events: list[tuple[str, dict]] = []   # ("menu", msg) oppure ("cfg:<dato>", callback)
seen_chats: list[tuple[int, str]] = []   # canali in cui il bot ha visto un messaggio (id, titolo)


def get_decisions(offset: int, wait: int = 0) -> tuple[list[tuple[str, int, dict]], int]:
    """Ritorna [(azione, post_id, callback)], nuovo offset. Con wait>0 resta in ascolto fino a wait secondi."""
    updates = _api("getUpdates", data={"offset": offset, "timeout": wait,
                                       "allowed_updates": json.dumps(["callback_query", "message", "channel_post"])})
    out = []
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        cp = u.get("channel_post")
        if cp:
            seen_chats.append((cp["chat"]["id"], cp["chat"].get("title", "")))
            continue
        msg = u.get("message")
        if msg and str(msg.get("from", {}).get("id")) == str(config.ADMIN_CHAT_ID) \
                and (msg.get("text") or "").split("@")[0].strip() in ("/impostazioni", "/menu", "/start"):
            menu_events.append(("menu", msg))
            continue
        cq = u.get("callback_query")
        if not cq or str(cq["from"]["id"]) != str(config.ADMIN_CHAT_ID):
            continue
        if cq.get("data", "").startswith("cfg:"):
            menu_events.append((cq["data"], cq))
            continue
        action, _, pid = cq.get("data", "").partition(":")
        if action in ("ok", "no") and pid.isdigit():
            out.append((action, int(pid), cq))
    return out, offset


def ack(cq: dict, text: str):
    try:
        _api("answerCallbackQuery", data={"callback_query_id": cq["id"], "text": text})
    except RuntimeError:
        pass  # le callback scadono dopo un po': non è un problema


def mark(message_id: int, text: str):
    """Sostituisce i pulsanti con lo stato finale."""
    try:
        _api("editMessageReplyMarkup", data={
            "chat_id": config.ADMIN_CHAT_ID, "message_id": message_id,
            "reply_markup": json.dumps({"inline_keyboard": [[{"text": text, "callback_data": "noop"}]]}),
        })
    except RuntimeError:
        pass


def notify(text: str):
    _api("sendMessage", data={"chat_id": config.ADMIN_CHAT_ID, "text": text})


def send_menu(text: str, keyboard: dict) -> int:
    return _api("sendMessage", data={"chat_id": config.ADMIN_CHAT_ID, "text": text,
                                     "reply_markup": json.dumps(keyboard)})["message_id"]


def edit_menu(message_id: int, text: str, keyboard: dict):
    try:
        _api("editMessageText", data={"chat_id": config.ADMIN_CHAT_ID, "message_id": message_id, "text": text,
                                      "reply_markup": json.dumps(keyboard)})
    except RuntimeError:
        pass  # "message is not modified" se non è cambiato nulla


def send_deal(chat_id, image: Path, caption_html: str, url: str):
    """Pubblica l'offerta su un canale: foto + testo + pulsante che apre Amazon (l'app, se installata)."""
    kb = {"inline_keyboard": [[{"text": "🛒 CLICCA QUI PER AGGIUNGERE AL CARRELLO", "url": url, "style": "success"}]]}
    with open(image, "rb") as f:
        return _api("sendPhoto", data={"chat_id": chat_id, "caption": caption_html[:1024], "parse_mode": "HTML",
                                       "reply_markup": json.dumps(kb)}, files={"photo": f})
