"""Menu /impostazioni su Telegram: pulsanti per cambiare filtri e quote dell'autodeals."""
from __future__ import annotations

from .categories import CATEGORIES

STEPS = {"smin": ("sconto_min", 5, 5, 85), "smax": ("sconto_max", 5, 20, 95), "pmin": ("prezzo_min", 5, 0, 500),
         "pmax": ("prezzo_max", 50, 20, 5000), "tot": ("max_al_giorno", 2, 1, 100),
         "rip": ("ripubblica_dopo_giorni", 1, 1, 60), "giro": ("max_per_giro", 1, 1, 10),
         "ogni": ("ogni_minuti", 10, 10, 240)}


def _btn(text, data):
    return {"text": text, "callback_data": f"cfg:{data}"}


def main_menu(cfg: dict) -> tuple[str, dict]:
    on = lambda b: "✅" if b else "❌"
    text = ("⚙️ Impostazioni autodeals\n\n"
            f"Sconto: {cfg['sconto_min']}% – {cfg['sconto_max']}%\n"
            f"Prezzo: {cfg['prezzo_min']}€ – {cfg['prezzo_max']}€\n"
            f"Massimo al giorno: {cfg['max_al_giorno']} (per giro: {cfg['max_per_giro']})\n"
            f"Controllo ogni {cfg['ogni_minuti']} min · stesso prodotto dopo {cfg['ripubblica_dopo_giorni']} giorni\n"
            f"Solo venduto da Amazon: {on(cfg['solo_amazon'])}\n"
            f"Sconto calcolato su: {'prezzo precedente (solo veri)' if cfg['base_sconto'] == 'was' else 'qualsiasi riferimento'}\n"
            f"Canale: {cfg['canale']}")
    kb = [[_btn("−", "smin-"), _btn(f"Sconto min {cfg['sconto_min']}%", "noop"), _btn("+", "smin+")],
          [_btn("−", "smax-"), _btn(f"Sconto max {cfg['sconto_max']}%", "noop"), _btn("+", "smax+")],
          [_btn("−", "pmin-"), _btn(f"Prezzo min {cfg['prezzo_min']}€", "noop"), _btn("+", "pmin+")],
          [_btn("−", "pmax-"), _btn(f"Prezzo max {cfg['prezzo_max']}€", "noop"), _btn("+", "pmax+")],
          [_btn("−", "tot-"), _btn(f"Max al giorno {cfg['max_al_giorno']}", "noop"), _btn("+", "tot+")],
          [_btn("−", "giro-"), _btn(f"Per giro {cfg['max_per_giro']}", "noop"), _btn("+", "giro+")],
          [_btn("−", "ogni-"), _btn(f"Ogni {cfg['ogni_minuti']} min", "noop"), _btn("+", "ogni+")],
          [_btn("−", "rip-"), _btn(f"Ripubblica dopo {cfg['ripubblica_dopo_giorni']} gg", "noop"), _btn("+", "rip+")],
          [_btn(f"{on(cfg['solo_amazon'])} Solo Amazon", "amz"),
           _btn("Sconto: solo prezzo precedente" if cfg["base_sconto"] == "was" else "Sconto: qualsiasi", "base")],
          [_btn("📦 Categorie e quote", "page:cat")],
          [_btn(f"{on(cfg['attivo'])} Autodeals {'acceso' if cfg['attivo'] else 'spento'}", "on"),
           _btn("🔎 Cerca ora", "now")]]
    return text, {"inline_keyboard": kb}


def cat_menu(cfg: dict) -> tuple[str, dict]:
    lines, kb = ["📦 Categorie e quote giornaliere\n"], []
    for cid, c in CATEGORIES.items():
        v = cfg["categorie"][cid]
        lines.append(f"{'✅' if v['attiva'] else '❌'} {c['label']}: {v['max_giorno']} al giorno")
        kb.append([_btn(("✅ " if v["attiva"] else "❌ ") + c["label"][:18], f"c:{cid}:t"),
                   _btn("−", f"c:{cid}:-"), _btn(str(v["max_giorno"]), "noop"), _btn("+", f"c:{cid}:+")])
    kb.append([_btn("⬅️ Indietro", "page:main")])
    return "\n".join(lines), {"inline_keyboard": kb}


def apply(data: str, settings: dict) -> str:
    """Applica un pulsante a `settings` (il dizionario completo salvato nello stato). Ritorna la pagina da mostrare
    ("main", "cat") o "now" se va lanciata una ricerca subito."""
    if data.startswith("page:"):
        return data[5:]
    if data == "now":
        settings["_now"] = True
        return "main"
    if data in ("amz", "base", "on"):
        if data == "amz":
            settings["solo_amazon"] = not settings["solo_amazon"]
        elif data == "base":
            settings["base_sconto"] = "any" if settings["base_sconto"] == "was" else "was"
        else:
            settings["attivo"] = not settings["attivo"]
        return "main"
    if data.startswith("c:"):
        _, cid, act = data.split(":")
        if cid in CATEGORIES:
            v = settings["categorie"][cid]
            if act == "t":
                v["attiva"] = not v["attiva"]
            else:
                v["max_giorno"] = max(0, min(50, v["max_giorno"] + (1 if act == "+" else -1)))
        return "cat"
    key, sign = data[:-1], data[-1]
    if key in STEPS and sign in "+-":
        name, step, lo, hi = STEPS[key]
        settings[name] = max(lo, min(hi, settings[name] + (step if sign == "+" else -step)))
        if settings["sconto_min"] > settings["sconto_max"]:
            settings["sconto_max"] = settings["sconto_min"]
        if settings["prezzo_min"] > settings["prezzo_max"]:
            settings["prezzo_max"] = settings["prezzo_min"]
    return "main"
