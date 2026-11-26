"""Impostazioni del Dr.Scount Bot Offerte: stanno in state.json (chiave "settings") e si cambiano da Telegram."""
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
    "casa_di_fila": 2,           # offerte di Casa di fila, poi 1 di un'altra categoria (0 = solo rotazione per quote)
    "max_per_giro": 2,           # offerte pubblicate a ogni controllo
    "ogni_minuti": 30,           # ogni quanto cerca
    "canale": "-1005617414476",  # canale di TEST (Dr.scount test); si cambia quando sei pronto
    # sconto_min: None = usa quello generale; un numero = soglia propria della categoria
    "categorie": {c: {"attiva": True, "max_giorno": DEFAULT_QUOTAS.get(c, 3), "sconto_min": None} for c in CATEGORIES},
}
DEFAULTS["categorie"]["casa"]["max_giorno"] = 12
DEFAULTS["categorie"]["elettrodomestici"].update({"max_giorno": 1, "sconto_min": 60})   # solo super offerte


def min_discount(cfg: dict, category: str) -> int:
    v = (cfg["categorie"].get(category) or {}).get("sconto_min")
    return cfg["sconto_min"] if v is None else v


def load(state: dict) -> dict:
    """Impostazioni salvate sopra i valori di partenza (le chiavi nuove compaiono da sole)."""
    s = copy.deepcopy(DEFAULTS)
    saved = state.get("settings") or {}
    for k, v in saved.items():
        if k == "categorie":
            for c, cv in v.items():
                if c in s["categorie"]:
                    s["categorie"][c].update(cv)
        elif k in s:   # (le chiavi che iniziano con _ , come _v, restano solo nello stato)
            s[k] = v
    return s
