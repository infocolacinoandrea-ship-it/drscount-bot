"""Testo del post Instagram."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from scraper import Offer

HASHTAGS = "#offerteamazon #amazonitalia #offerte #sconti #risparmio #casa #offertedelgiorno #drscount"


def build_caption(o: Offer) -> str:
    now = dt.datetime.now(ZoneInfo("Europe/Rome"))
    lines = [
        f"🔥 {o.short_title}",
        "",
        f"💰 A soli {o.price} invece di {o.old_price} (-{o.discount}%)",
    ]
    if o.historic_low:
        lines.append("📉 MINIMO STORICO!")
    for e in o.extra:
        lines.append(e)
    lines += [
        "",
        "👉 Il link per acquistare lo trovi sul nostro canale Telegram: LINK IN BIO!",
        "Ogni giorno le offerte Amazon migliori, soprattutto per la casa 🏠",
        "",
        HASHTAGS,
        "",
        f"Prezzo rilevato il {now:%d/%m/%Y} alle {now:%H:%M}, può cambiare in qualsiasi momento. "
        "In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei.",
    ]
    return "\n".join(lines)
