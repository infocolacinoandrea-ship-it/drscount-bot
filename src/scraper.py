"""Legge le offerte dalla pagina pubblica del canale (t.me/s/<canale>)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

PRICE_RE = re.compile(r"Al prezzo di\s*✅?\s*([\d.,]+)\s*€\s*invece di\s*❌?\s*([\d.,]+)\s*€\s*\((\d+)%\)", re.I)
REVIEWS_RE = re.compile(r"([\d.,]+)\s*Recensioni:\s*([\d.]+)\s*/\s*5", re.I)
ASIN_RE = re.compile(r"amazon\.[a-z.]+/(?:dp|gp/product)/([A-Z0-9]{10})")


@dataclass
class Offer:
    post_id: int
    title: str
    price: str
    old_price: str
    discount: int
    historic_low: bool
    reviews: int
    rating: float
    asin: str | None
    link: str | None
    photo_url: str | None
    date: str
    extra: list[str] = field(default_factory=list)

    @property
    def short_title(self) -> str:
        return clean_title(self.title)


# Parole con cui un titolo non può finire ("Videocamera Blink con" -> "Videocamera Blink")
_DANGLING = {"con", "per", "e", "ed", "di", "da", "del", "della", "dei", "degli", "delle", "a", "al", "alla",
             "ai", "in", "su", "il", "lo", "la", "le", "i", "gli", "un", "una", "o", "+", "&", "-", "–", "/",
             "senza", "tra", "fra", "with", "and", "for", "the", "of"}
# Dove il titolo "naturale" del prodotto di solito finisce
_BREAKS = re.compile(r"\s(?:con|per|senza|ideale|adatto|adatta|compatibile|include|incluso|inclusa)\s", re.I)


def clean_title(title: str, max_len: int = 42) -> str:
    """Titolo breve e sempre finito: niente frasi troncate, niente puntini, niente parole appese."""
    t = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", title)        # via le parentesi: (ultimo modello)
    t = re.sub(r"\.{2,}|…", "", t).strip(" .,-–|")
    parts = [p.strip() for p in re.split(r",| - | – |\||;", t) if p.strip()]
    if not parts:
        return title.strip()[:max_len]
    t = parts[0]
    # se il primo pezzo è solo il marchio (es. "Dermolab - Crema viso..."), aggiunge il pezzo dopo
    if len(t) < 14 and len(parts) > 1 and not parts[1].isupper():
        t = f"{t} {parts[1]}"
    # taglia alla prima "congiunzione" se il titolo è lungo (dopo c'è la descrizione, non il nome)
    if len(t) > max_len:
        m = _BREAKS.search(t, 12)
        if m and m.start() >= 12:
            t = t[: m.start()]
    # se è ancora troppo lungo taglia sull'ultima parola intera
    if len(t) > max_len:
        t = t[: max_len + 1].rsplit(" ", 1)[0]
    words = t.split()
    while len(words) > 1 and words[-1].lower().strip(".,:;") in _DANGLING:
        words.pop()
    # parole TUTTE MAIUSCOLE -> Maiuscola iniziale (ALPRO BARISTA -> Alpro Barista)
    words = [w.capitalize() if w.isalpha() and w.isupper() and len(w) > 3 else w for w in words]
    return " ".join(words).strip(" .,:;-–/+&")


def _to_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s) or 0)


def parse_message(msg) -> Offer | None:
    text_el = msg.select_one(".tgme_widget_message_text")
    if not text_el:
        return None
    for br in text_el.find_all("br"):
        br.replace_with("\n")
    text = text_el.get_text()
    m = PRICE_RE.search(text)
    if not m:
        return None
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = lines[0]
    rv = REVIEWS_RE.search(text)
    link_el = next((a for a in text_el.find_all("a") if "amazon." in a.get("href", "")), None)
    link = link_el["href"] if link_el else None
    asin = ASIN_RE.search(link).group(1) if link and ASIN_RE.search(link) else None
    photo = None
    wrap = msg.select_one(".tgme_widget_message_photo_wrap")
    if wrap:
        pm = re.search(r"url\(['\"]?(.*?)['\"]?\)", wrap.get("style", ""))
        photo = pm.group(1) if pm else None
    extra = [l for l in lines if "checkout" in l.lower() or "coupon" in l.lower() or "codice" in l.lower()]
    time_el = msg.select_one("time")
    return Offer(
        post_id=int(msg["data-post"].split("/")[-1]),
        title=title,
        price=m.group(1) + "€",
        old_price=m.group(2) + "€",
        discount=int(m.group(3)),
        historic_low="MINIMO STORICO" in text.upper(),
        reviews=_to_int(rv.group(1)) if rv else 0,
        rating=float(rv.group(2)) if rv else 0.0,
        asin=asin,
        link=link,
        photo_url=photo,
        date=time_el["datetime"] if time_el else "",
        extra=extra,
    )


def parse_html(html: str) -> list[Offer]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for msg in soup.select(".tgme_widget_message[data-post]"):
        o = parse_message(msg)
        if o:
            out.append(o)
    return out


def fetch_offers(channel: str, pages: int = 2) -> list[Offer]:
    """Scarica gli ultimi ~20*pages messaggi del canale."""
    offers: dict[int, Offer] = {}
    url = f"https://t.me/s/{channel}"
    before = None
    for _ in range(pages):
        r = requests.get(url, params={"before": before} if before else None, headers=UA, timeout=30)
        r.raise_for_status()
        batch = parse_html(r.text)
        for o in batch:
            offers[o.post_id] = o
        ids = [int(x.split("/")[-1]) for x in re.findall(r'data-post="[^"]+/(\d+)"', r.text)]
        if not ids:
            break
        before = min(ids)
    return sorted(offers.values(), key=lambda o: o.post_id)


def download(url: str) -> bytes:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.content
