"""Impostazioni dell'autodeals: stanno in state.json (chiave "settings") e si cambiano da Telegram."""
import copy

from .categories import CATEGORIES, DEFAULT_QUOTAS

DEFAULTS = {
    "attivo": True,
    "sconto_min": 40,            # % minima
    "sconto_max": 90,            # % massima (sopra di solito è un errore di prezzo)
    "prezzo_min": 5,             # €
    "prezzo_max": 1500,          # €
    "solo_amazon": True,         # solo prodotti venduti da Amazon
    "base_sconto": "any",        # "any" = qualsiasi riferimento; "was" = solo prezzo precedente (più affidabile)
    "ripubblica_dopo_giorni": 14,
    "max_al_giorno": 20,
    "max_per_giro": 2,           # offerte pubblicate a ogni controllo
    "ogni_minuti": 30,           # ogni quanto cerca
    "canale": "-1005617414476",  # canale di TEST (Dr.scount test); si cambia quando sei pronto
    "categorie": {c: {"attiva": True, "max_giorno": DEFAULT_QUOTAS.get(c, 3)} for c in CATEGORIES},
}


def load(state: dict) -> dict:
    """Impostazioni salvate sopra i valori di partenza (le chiavi nuove compaiono da sole)."""
    s = copy.deepcopy(DEFAULTS)
    saved = state.get("settings") or {}
    for k, v in saved.items():
        if k == "categorie":
            for c, cv in v.items():
                if c in s["categorie"]:
                    s["categorie"][c].update(cv)
        elif k in s:
            s[k] = v
    return s
