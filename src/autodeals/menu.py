"""Menu /impostazioni su Telegram: pagine con pulsanti grandi (uno per riga) e spiegazioni in italiano semplice.
Ogni pulsante modifica lo stesso messaggio, così il valore nuovo si vede subito."""
from __future__ import annotations

from .categories import CATEGORIES

# nome breve -> (impostazione, passo, minimo, massimo)
STEPS = {"smin": ("sconto_min", 5, 5, 85), "smax": ("sconto_max", 5, 20, 95), "pmin": ("prezzo_min", 5, 0, 500),
         "pmax": ("prezzo_max", 50, 20, 5000), "tot": ("max_al_giorno", 2, 1, 100),
         "rip": ("ripubblica_dopo_giorni", 1, 1, 60), "giro": ("max_per_giro", 1, 1, 10), "cdf": ("casa_di_fila", 1, 0, 4),
         "ogni": ("ogni_minuti", 10, 10, 240)}


def _b(text, data, style=None):
    b = {"text": text, "callback_data": f"cfg:{data}"}
    if style:
        b["style"] = style      # "success" verde, "danger" rosso, "primary" blu (app Telegram aggiornate)
    return b


def _pair(label_minus, key_minus, label_plus, key_plus):
    return [_b(label_minus, key_minus, "danger"), _b(label_plus, key_plus, "success")]


def _back(page="main"):
    return [_b("⬅️ Indietro", f"page:{page}")]


def render(page: str, cfg: dict) -> tuple[str, dict]:
    if page == "sconto":
        return (f"🎯 SCONTO\n\nPubblico solo offerte con sconto da {cfg['sconto_min']}% a {cfg['sconto_max']}%.\n\n"
                "• Il minimo toglie le offerte poco convenienti.\n"
                "• Il massimo toglie gli sconti troppo alti per essere veri (spesso sono errori di prezzo).",
                {"inline_keyboard": [
                    _pair("➖ Minimo −5%", "smin-", "➕ Minimo +5%", "smin+"),
                    _pair("➖ Massimo −5%", "smax-", "➕ Massimo +5%", "smax+"), _back()]})
    if page == "prezzo":
        return (f"💶 PREZZO\n\nPubblico solo prodotti che costano da {cfg['prezzo_min']}€ a {cfg['prezzo_max']}€ "
                "(il prezzo scontato, quello che paga chi compra).",
                {"inline_keyboard": [
                    _pair("➖ Minimo −5€", "pmin-", "➕ Minimo +5€", "pmin+"),
                    _pair("➖ Massimo −50€", "pmax-", "➕ Massimo +50€", "pmax+"), _back()]})
    if page == "ritmo":
        return (f"⏱ QUANTE E QUANDO\n\n• Al giorno al massimo: {cfg['max_al_giorno']} offerte (in tutto)\n"
                f"• A ogni controllo ne pubblico fino a: {cfg['max_per_giro']}\n"
                f"• Cerco nuove offerte ogni: {cfg['ogni_minuti']} minuti\n"
                f"• Schema: {str(cfg['casa_di_fila']) + ' di Casa di fila, poi 1 di un altra categoria' if cfg['casa_di_fila'] else 'solo rotazione per quote'}\n"
                f"• Lo stesso prodotto lo ripubblico dopo: {cfg['ripubblica_dopo_giorni']} giorni",
                {"inline_keyboard": [
                    _pair("➖ Al giorno −2", "tot-", "➕ Al giorno +2", "tot+"),
                    _pair("➖ Per controllo −1", "giro-", "➕ Per controllo +1", "giro+"),
                    _pair("➖ Ogni −10 min", "ogni-", "➕ Ogni +10 min", "ogni+"),
                    _pair("➖ Casa di fila −1", "cdf-", "➕ Casa di fila +1", "cdf+"),
                    _pair("➖ Ripubblica −1 giorno", "rip-", "➕ Ripubblica +1 giorno", "rip+"), _back()]})
    if page == "filtri":
        was = cfg["base_sconto"] == "was"
        return ("🛡 FILTRI\n\n"
                f"• Venduto da Amazon: {'SÌ, solo prodotti venduti e spediti da Amazon' if cfg['solo_amazon'] else 'NO, anche altri venditori'}\n"
                f"• Calcolo dello sconto: {'solo sul prezzo precedente reale (pochi ma affidabili)' if was else 'su qualsiasi prezzo di riferimento di Amazon (molte offerte, ma lo sconto può essere gonfiato)'}",
                {"inline_keyboard": [
                    [_b("✅ Solo Amazon: SÌ — tocca per cambiare" if cfg["solo_amazon"] else "❌ Solo Amazon: NO — tocca per cambiare",
                        "amz", "success" if cfg["solo_amazon"] else "danger")],
                    [_b("Sconto: solo prezzo reale — cambia" if was else "Sconto: qualsiasi riferimento — cambia", "base")],
                    _back()]})
    if page == "cat":
        rows = []
        for cid, c in CATEGORIES.items():
            v = cfg["categorie"][cid]
            rows.append([_b(f"{'✅' if v['attiva'] else '❌'} {c['label']} · {v['max_giorno']} al giorno" if v["attiva"]
                            else f"❌ {c['label']} · spenta", f"page:c:{cid}")])
        rows.append(_back())
        tot = sum(v["max_giorno"] for v in cfg["categorie"].values() if v["attiva"])
        return ("📦 CATEGORIE\n\nTocca una categoria per accenderla, spegnerla o cambiare quante offerte al giorno "
                f"pubblicare.\n\nSomma delle quote attive: {tot} (il tetto totale è {cfg['max_al_giorno']} al giorno).",
                {"inline_keyboard": rows})
    if page.startswith("c:"):
        cid = page[2:]
        c, v = CATEGORIES[cid], cfg["categorie"][cid]
        own = v.get("sconto_min")
        return (f"📦 {c['label'].upper()}\n\nStato: {'ACCESA' if v['attiva'] else 'SPENTA'}\n"
                f"Offerte al giorno: {v['max_giorno']}\n"
                f"Sconto minimo: {own if own is not None else cfg['sconto_min']}%"
                f"{' (solo per questa categoria)' if own is not None else ' (quello generale)'}",
                {"inline_keyboard": [
                    [_b("✅ Accesa — tocca per spegnere" if v["attiva"] else "❌ Spenta — tocca per accendere",
                        f"c:{cid}:t", "success" if v["attiva"] else "danger")],
                    _pair("➖ Una in meno al giorno", f"c:{cid}:-", "➕ Una in più al giorno", f"c:{cid}:+"),
                    _pair("➖ Sconto min −5%", f"c:{cid}:sm-", "➕ Sconto min +5%", f"c:{cid}:sm+"),
                    [_b("↩️ Usa lo sconto generale", f"c:{cid}:smr")],
                    _back("cat")]})
    # pagina principale
    cats = [c["label"] for cid, c in CATEGORIES.items() if cfg["categorie"][cid]["attiva"]]
    text = ("⚙️ IMPOSTAZIONI · DR.SCOUNT BOT OFFERTE\n\n"
            f"Stato: {'🟢 ACCESO' if cfg['attivo'] else '🔴 SPENTO'}\n"
            f"🎯 Sconto: {cfg['sconto_min']}% – {cfg['sconto_max']}%\n"
            f"💶 Prezzo: {cfg['prezzo_min']}€ – {cfg['prezzo_max']}€\n"
            f"📦 Categorie accese: {len(cats)} su {len(CATEGORIES)}\n"
            f"⏱ Fino a {cfg['max_al_giorno']} offerte al giorno, controllo ogni {cfg['ogni_minuti']} min\n"
            f"📢 Pubblico su: {cfg['canale']}\n\nTocca una voce per cambiarla.")
    return text, {"inline_keyboard": [
        [_b("🎯 Sconto", "page:sconto")], [_b("💶 Prezzo", "page:prezzo")], [_b("📦 Categorie e quote", "page:cat")],
        [_b("⏱ Quante e quando", "page:ritmo")], [_b("🛡 Filtri", "page:filtri")],
        [_b("🟢 Acceso — tocca per spegnere" if cfg["attivo"] else "🔴 Spento — tocca per accendere", "on",
            "success" if cfg["attivo"] else "danger")],
        [_b("🔎 Cerca offerte adesso", "now", "primary")]]}


def apply(data: str, settings: dict) -> str:
    """Applica un pulsante a `settings`. Ritorna la pagina da mostrare."""
    if data.startswith("page:"):
        return data[5:]
    if data == "now":
        settings["_now"] = True
        return "main"
    if data in ("amz", "base", "on"):
        if data == "amz":
            settings["solo_amazon"] = not settings["solo_amazon"]
            return "filtri"
        if data == "base":
            settings["base_sconto"] = "any" if settings["base_sconto"] == "was" else "was"
            return "filtri"
        settings["attivo"] = not settings["attivo"]
        return "main"
    if data.startswith("c:"):
        _, cid, act = data.split(":")
        if cid in CATEGORIES:
            v = settings["categorie"][cid]
            if act == "t":
                v["attiva"] = not v["attiva"]
            elif act in ("sm+", "sm-"):
                base = v.get("sconto_min")
                base = settings["sconto_min"] if base is None else base
                v["sconto_min"] = max(5, min(95, base + (5 if act == "sm+" else -5)))
            elif act == "smr":
                v["sconto_min"] = None
            else:
                v["max_giorno"] = max(0, min(50, v["max_giorno"] + (1 if act == "+" else -1)))
        return f"c:{cid}"
    key, sign = data[:-1], data[-1]
    if key in STEPS and sign in "+-":
        name, step, lo, hi = STEPS[key]
        settings[name] = max(lo, min(hi, settings[name] + (step if sign == "+" else -step)))
        if settings["sconto_min"] > settings["sconto_max"]:
            settings["sconto_max"] = settings["sconto_min"]
        if settings["prezzo_min"] > settings["prezzo_max"]:
            settings["prezzo_max"] = settings["prezzo_min"]
        return {"smin": "sconto", "smax": "sconto", "pmin": "prezzo", "pmax": "prezzo"}.get(key, "ritmo")
    return "main"
