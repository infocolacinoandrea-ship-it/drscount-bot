"""Bot Telegram: ti manda le anteprime e legge i tuoi ✅ / ❌."""
from __future__ import annotations

import json
from pathlib import Path

import requests

import config


def _api(method: str, **kwargs):
    r = requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}", timeout=90, **kwargs)
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


def get_decisions(offset: int, wait: int = 0) -> tuple[list[tuple[str, int, dict]], int]:
    """Ritorna [(azione, post_id, callback)], nuovo offset. Con wait>0 resta in ascolto fino a wait secondi."""
    updates = _api("getUpdates", data={"offset": offset, "timeout": wait,
                                       "allowed_updates": json.dumps(["callback_query", "message"])})
    out = []
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        cq = u.get("callback_query")
        if not cq or str(cq["from"]["id"]) != str(config.ADMIN_CHAT_ID):
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
