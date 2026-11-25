"""Trova le offerte: cerca per categoria, trasforma i risultati, applica filtri e quote."""
import datetime as dt
from dataclasses import dataclass

from scraper import clean_title

import re

from .categories import CATEGORIES
from .client import PARTNER_TAG, CreatorsClient


@dataclass
class Deal:
    asin: str
    title: str
    price: float
    old_price: float
    discount: int
    basis: str            # "WAS_PRICE" (prezzo precedente) o "LIST_PRICE" (prezzo consigliato)
    seller: str
    photo_url: str
    category: str
    link: str
    full_title: str = ""
    reviews: int = 0
    rating: float = 0.0
    historic_low: bool = False

    @property
    def price_txt(self) -> str:
        return _eur(self.price)

    @property
    def old_price_txt(self) -> str:
        return _eur(self.old_price)


def _eur(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "€"


def clean_link(asin: str) -> str:
    """Link breve e pulito: mostra chiaramente che va su Amazon e mantiene il tag."""
    return f"https://www.amazon.it/dp/{asin}?tag={PARTNER_TAG}"


def parse_item(item: dict, category: str) -> Deal | None:
    """Trasforma un prodotto grezzo dell'API in un Deal, o None se non ha un'offerta con sconto."""
    try:
        listings = (item.get("offersV2") or {}).get("listings") or []
        # la offerta "principale": quella che vince il carrello, senza Iscriviti e Risparmia
        main = [l for l in listings if l.get("isBuyBoxWinner") and not l.get("type")] \
            or [l for l in listings if not l.get("type")]
        if not main:
            return None
        pr = main[0]["price"]
        price = float(pr["money"]["amount"])
        basis = pr["savingBasis"]
        old = float(basis["money"]["amount"])
        pct = int((pr.get("savings") or {}).get("percentage") or round((1 - price / old) * 100))
        photo = item["images"]["primary"]["large"]["url"]
        raw_title = item["itemInfo"]["title"]["displayValue"]
        title = clean_title(raw_title)
        asin = item["asin"]
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    if old <= price or not title or not photo:
        return None
    cr = item.get("customerReviews") or {}
    deal = Deal(full_title=clean_title(raw_title, max_len=110), reviews=int(((cr.get("count") or {}).get("value") if isinstance(cr.get("count"), dict) else cr.get("count")) or 0),
                rating=float(((cr.get("starRating") or {}).get("value") if isinstance(cr.get("starRating"), dict) else cr.get("starRating")) or 0),
                asin=asin, title=title, price=price, old_price=old, discount=pct,
                basis=basis.get("savingBasisType", ""), seller=(main[0].get("merchantInfo") or {}).get("name", ""),
                photo_url=photo, category=category, link=clean_link(asin))
    return deal if fits_category(deal) else None


def _has(title: str, words: list[str]) -> bool:
    t = title.lower()
    return any(re.search(r"(?<![\wàèéìòù])" + re.escape(w) + r"(?![\wàèéìòù])", t) for w in words)


def fits_category(d: Deal) -> bool:
    """Controllo del titolo: il prodotto deve essere davvero di quella categoria (non un accessorio,
    non un prodotto capitato lì per via dell'indice di Amazon)."""
    rules = CATEGORIES.get(d.category) or {}
    if rules.get("must") and not _has(d.title, rules["must"]):
        return False
    if rules.get("not") and _has(d.title, rules["not"]):
        return False
    return d.price >= rules.get("prezzo_min", 0)


def passes(d: Deal, cfg: dict) -> bool:
    """Filtri generali (le quote giornaliere si applicano dopo)."""
    if not (cfg["sconto_min"] <= d.discount <= cfg["sconto_max"]):
        return False
    if not (cfg["prezzo_min"] <= d.price <= cfg["prezzo_max"]):
        return False
    if cfg["solo_amazon"] and d.seller.lower() != "amazon":
        return False
    if cfg["base_sconto"] == "was" and d.basis != "WAS_PRICE":
        return False
    return True


def today_counts(state: dict) -> dict:
    """Quante offerte per categoria sono già uscite oggi (fuso orario italiano)."""
    day = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).strftime("%Y-%m-%d")
    return (state.get("deals_daily") or {}).get(day, {})


def not_recent(d: Deal, state: dict, days: int) -> bool:
    seen = (state.get("deals_seen") or {}).get(d.asin)
    if not seen:
        return True
    return dt.datetime.fromisoformat(seen) < dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)


def title_key(d: Deal) -> str:
    """Chiave per riconoscere lo stesso prodotto in varianti diverse (colore, taglia: ASIN diversi, stesso titolo)."""
    return re.sub(r"[^a-z0-9]+", " ", d.title.lower()).strip()


def title_recent(d: Deal, state: dict, days: int) -> bool:
    seen = (state.get("deals_titles") or {}).get(title_key(d))
    return bool(seen) and dt.datetime.fromisoformat(seen) >= dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)


def pick(candidates: list[Deal], cfg: dict, state: dict, limit: int = 1) -> list[Deal]:
    """Sceglie fra i candidati rispettando tutto: filtri, doppioni, quote per categoria e tetto giornaliero.
    Ordine: sconto più alto per prima."""
    counts = today_counts(state)
    total = sum(counts.values())
    out: list[Deal] = []
    for d in sorted(candidates, key=lambda x: -x.discount):
        cat = cfg["categorie"].get(d.category) or {}
        if not cat.get("attiva", False) or not passes(d, cfg) or not not_recent(d, state, cfg["ripubblica_dopo_giorni"]):
            continue
        if counts.get(d.category, 0) + sum(1 for o in out if o.category == d.category) >= cat.get("max_giorno", 0):
            continue
        if total + len(out) >= cfg["max_al_giorno"] or any(o.asin == d.asin for o in out):
            continue
        # stesso prodotto in un'altra variante (colore/taglia) già scelto ora o pubblicato di recente
        if any(title_key(o) == title_key(d) for o in out) or title_recent(d, state, cfg["ripubblica_dopo_giorni"]):
            continue
        out.append(d)
        if len(out) >= limit:
            break
    return out


def scan(client: CreatorsClient, cfg: dict, state: dict, per_category: int = 2) -> list[Deal]:
    """Cerca nelle categorie attive. Per ogni categoria usa a rotazione alcune parole chiave
    (l'indice di rotazione sta nello stato, così ogni giro guarda prodotti diversi)."""
    rot = state.setdefault("deals_rotation", {})
    found: list[Deal] = []
    for cid, cat in CATEGORIES.items():
        if not cfg["categorie"].get(cid, {}).get("attiva"):
            continue
        kws = cat["keywords"]
        start = rot.get(cid, 0)
        for i in range(per_category):
            kw, _, idx = kws[(start + i) % len(kws)].partition("|")   # "parola|Indice" per cambiare indice
            try:
                items = client.search(kw, idx or cat["index"], min_saving=cfg["sconto_min"])
            except RuntimeError as e:
                print(f"[autodeals] {cid}/{kw}: {e}")
                continue
            for it in items:
                d = parse_item(it, cid)
                if d:
                    found.append(d)
        rot[cid] = (start + per_category) % len(kws)
    return found
