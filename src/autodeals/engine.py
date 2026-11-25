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
    full = d.full_title or d.title      # il titolo lungo: quello corto può aver perso parole importanti
    if rules.get("must") and not _has(full, rules["must"]):
        return False
    if rules.get("not") and _has(full, rules["not"]):
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


_BULK = re.compile(r"(\d+)\s*(?:x\s*)?(pastiglie|tabs|rotoli|lavaggi|capsule|pezzi|pz|fogli|sacchetti)|pacco|scorta|maxi|"
                  r"confezione da|\d+\s*x\s*\d+", re.I)


def priority(d: Deal) -> int:
    """2 = prima necessità in formato scorta, 1 = prima necessità, 0 = tutto il resto (solo categoria casa)."""
    words = (CATEGORIES.get(d.category) or {}).get("essenziali_parole")
    if not words or not _has(d.full_title or d.title, words):
        return 0
    return 2 if _BULK.search(d.full_title or d.title) else 1


def pick(candidates: list[Deal], cfg: dict, state: dict, limit: int = 1) -> list[Deal]:
    """Sceglie a rotazione fra le categorie, in proporzione alle quote (smooth weighted round-robin):
    con casa 6, cura persona 4, elettronica 3 esce per esempio casa, cura, casa, elettronica, casa, cura...
    Dentro ogni categoria prima lo sconto più alto. Rispetta filtri, doppioni, quote e tetto giornaliero.
    La rotazione continua da un controllo all'altro (state["deals_wrr"])."""
    counts = today_counts(state)
    total = sum(counts.values())
    queues: dict[str, list[Deal]] = {}
    for d in sorted(candidates, key=lambda x: (-priority(x), -x.discount)):
        cat = cfg["categorie"].get(d.category) or {}
        if not cat.get("attiva", False) or not passes(d, cfg) or not not_recent(d, state, cfg["ripubblica_dopo_giorni"]):
            continue
        if title_recent(d, state, cfg["ripubblica_dopo_giorni"]):
            continue
        queues.setdefault(d.category, []).append(d)
    cur = state.setdefault("deals_wrr", {})
    out: list[Deal] = []
    while len(out) < limit and total + len(out) < cfg["max_al_giorno"]:
        avail = {}
        for c, q in queues.items():
            quota = cfg["categorie"][c].get("max_giorno", 0)
            if q and counts.get(c, 0) + sum(1 for o in out if o.category == c) < quota:
                avail[c] = quota
        if not avail:
            break
        for c, w in avail.items():
            cur[c] = cur.get(c, 0) + w
        best = max(avail, key=lambda c: cur[c])
        cur[best] -= sum(avail.values())
        q = queues[best]
        while q:
            d = q.pop(0)
            if any(o.asin == d.asin or title_key(o) == title_key(d) for o in out):
                continue
            out.append(d)
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
        plan = [kws[(start + i) % len(kws)] for i in range(per_category)]
        ess = cat.get("essenziali")
        if ess:   # le cose di prima necessità si cercano a ogni giro (2 a rotazione) oltre alle altre parole
            e0 = rot.get(cid + ":ess", 0)
            plan += [ess[(e0 + i) % len(ess)] for i in range(2)]
            rot[cid + ":ess"] = (e0 + 2) % len(ess)
        for entry in plan:
            kw, _, idx = entry.partition("|")   # "parola|Indice" per cambiare indice
            try:
                items = client.search(kw, idx or cat["index"], min_saving=cfg["sconto_min"])
            except RuntimeError as e:
                print(f"[bot-offerte] {cid}/{kw}: {e}")
                continue
            for it in items:
                d = parse_item(it, cid)
                if d:
                    found.append(d)
        rot[cid] = (start + per_category) % len(kws)
    return found
