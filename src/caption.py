"""Testo del post Instagram."""
from __future__ import annotations

from scraper import Offer

HASHTAGS = "#offerteamazon #amazonitalia #offerte #sconti #casa"  # massimo 5


def build_caption(o: Offer) -> str:
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
    ]
    return "\n".join(lines)


def normalize(text: str, max_tags: int = 5) -> str:
    """Toglie tutto quello che segue la riga degli hashtag e tiene al massimo 5 hashtag.
    Serve anche per le anteprime create con la versione precedente."""
    out = []
    for line in text.split("\n"):
        if line.strip().startswith("#"):
            tags = [t for t in line.split() if t.startswith("#")][:max_tags]
            out.append(" ".join(tags))
            break
        out.append(line)
    return "\n".join(out).strip()
