"""Prove senza rete: esegui con  python tests/test_autodeals.py"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from autodeals import engine, settings

ITEM = {"asin": "B0TEST0001", "images": {"primary": {"large": {"url": "https://x/y.jpg"}}},
        "itemInfo": {"title": {"displayValue": "Omino Bianco Detersivo Lavatrice, 2000 ml x 3 | Smacchia in profondità"}},
        "offersV2": {"listings": [
            {"isBuyBoxWinner": True, "merchantInfo": {"name": "Amazon"},
             "price": {"money": {"amount": 10.99}, "savingBasis": {"money": {"amount": 29.99},
                                                                 "savingBasisType": "WAS_PRICE"},
                       "savings": {"percentage": 63}}},
            {"isBuyBoxWinner": False, "type": "SUBSCRIBE_AND_SAVE", "merchantInfo": {"name": "Amazon"},
             "price": {"money": {"amount": 9.0}, "savingBasis": {"money": {"amount": 29.99}},
                       "savings": {"percentage": 70}}}]}}


def mk(asin, pct, cat, seller="Amazon", basis="WAS_PRICE", price=20.0, title=None):
    return engine.Deal(asin, title or "marca" + "".join("abcdefghij"[int(c)] if c.isdigit() else c for c in asin), price, price * 100 / (100 - pct), pct, basis, seller, "u", cat, "l")


d = engine.parse_item(ITEM, "casa")
assert d and d.discount == 63 and d.price == 10.99 and d.basis == "WAS_PRICE", d
assert d.price_txt == "10,99€" and d.old_price_txt == "29,99€" and d.title.startswith("Omino Bianco")
assert d.link == "https://www.amazon.it/dp/B0TEST0001?tag=drscount06-21"
bad = dict(ITEM, offersV2={"listings": [{"isBuyBoxWinner": True, "price": {"money": {"amount": 5}}}]})
assert engine.parse_item(bad, "casa") is None   # nessuno sconto -> scartato

cfg = settings.load({})
assert cfg["sconto_min"] == 40
assert not engine.passes(mk("a", 30, "casa"), cfg)            # sotto il 40%
assert not engine.passes(mk("a", 95, "casa"), cfg)            # sopra il massimo
assert not engine.passes(mk("a", 50, "casa", seller="Pincopallino"), cfg)
assert engine.passes(mk("a", 50, "casa"), cfg)
cfg["base_sconto"] = "was"
assert not engine.passes(mk("a", 50, "casa", basis="LIST_PRICE"), cfg)

# quote per categoria e tetto giornaliero
cfg = settings.load({"settings": {"categorie": {"elettrodomestici": {"max_giorno": 1}}, "max_al_giorno": 3}})
cands = [mk("e1", 60, "elettrodomestici"), mk("e2", 55, "elettrodomestici"), mk("c1", 50, "casa"),
         mk("c2", 45, "casa"), mk("c3", 41, "casa")]
got = engine.pick(cands, cfg, {}, limit=10)
assert [x.asin for x in got] == ["c1", "c2", "c3"], [x.asin for x in got]   # casa pesa di più; tetto 3

# già pubblicati oggi + doppioni recenti
day = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).strftime("%Y-%m-%d")
st = {"deals_daily": {day: {"elettrodomestici": 1}}, "deals_seen": {"c1": dt.datetime.now(dt.timezone.utc).isoformat()}}
got = engine.pick(cands, cfg, st, limit=10)
assert [x.asin for x in got] == ["c2", "c3"], [x.asin for x in got]       # e* esaurito, c1 già visto
# categoria spenta
cfg["categorie"]["casa"]["attiva"] = False
assert engine.pick(cands, cfg, {}, limit=10)[0].category == "elettrodomestici"
# controllo categoria sul titolo
def it(title, price=300.0):
    x = dict(ITEM); x["itemInfo"] = {"title": {"displayValue": title}}
    x["offersV2"] = {"listings": [{"isBuyBoxWinner": True, "merchantInfo": {"name": "Amazon"},
        "price": {"money": {"amount": price}, "savingBasis": {"money": {"amount": price * 2}, "savingBasisType": "LIST_PRICE"},
                  "savings": {"percentage": 50}}}]}
    return x
E = "elettrodomestici"
assert engine.parse_item(it("Bosch Lavatrice 9 kg 1400 giri"), E)
assert engine.parse_item(it("Samsung Smart TV 55 pollici 4K"), E)
assert engine.parse_item(it("Candy Frigorifero Combinato 300 L"), E)
assert not engine.parse_item(it("Supporto TV da parete per 32-65 pollici"), E)       # accessorio
assert not engine.parse_item(it("Tubo di scarico per lavatrice 3 m"), E)               # ricambio
assert not engine.parse_item(it("Mobile TV moderno con cassetti"), E)
assert not engine.parse_item(it("Lavatrice giocattolo", 20.0), E)                      # sotto il prezzo minimo
assert not engine.parse_item(it("Zaino per il laptop impermeabile"), "casa")           # non è casa
assert engine.parse_item(it("Set di pentole antiaderenti 8 pezzi", 40.0), "casa")
# varianti dello stesso prodotto (ASIN diversi, stesso titolo): ne esce una sola
v1, v2 = mk("v1", 60, "casa", title="Pannolini Pampers"), mk("v2", 55, "casa", title="Pannolini Pampers")
cfg2 = settings.load({})
assert [x.asin for x in engine.pick([v1, v2, mk("v3", 50, "casa", title="Altro")], cfg2, {}, limit=5)] == ["v1", "v3"]
st2 = {"deals_titles": {engine.title_key(v1): dt.datetime.now(dt.timezone.utc).isoformat()}}
assert engine.pick([v2], cfg2, st2, limit=5) == []
# rotazione fra categorie in proporzione alle quote (casa 4, cura 2, elettronica 1)
cfg3 = settings.load({"settings": {"max_al_giorno": 50, "categorie": {c: {"attiva": False} for c in
                                    settings.DEFAULTS["categorie"]}}})
for c, n in (("casa", 4), ("cura_persona", 2), ("elettronica", 1)):
    cfg3["categorie"][c] = {"attiva": True, "max_giorno": n}
pool = [mk(f"{c}{i}", 70 - i, c) for c, n in (("casa", 6), ("cura_persona", 4), ("elettronica", 3)) for i in range(n)]
seq = [x.category for x in engine.pick(pool, cfg3, {}, limit=20)]
assert seq.count("casa") == 4 and seq.count("cura_persona") == 2 and seq.count("elettronica") == 1, seq
assert seq[:3] != ["casa"] * 3 and seq[0] == "casa" and "cura_persona" in seq[:3], seq   # alternate, non a blocchi
print("sequenza:", seq)
# casa: prima necessità e formato scorta davanti agli altri, anche con sconto più basso
cfgc = settings.load({"settings": {"categorie": {"casa": {"max_giorno": 3}}}})
a = mk("x1", 70, "casa", title="Set di pentole antiaderenti 8 pezzi")
b = mk("x2", 45, "casa", title="Finish Quantum Pastiglie Lavastoviglie, 120 Lavaggi")
c = mk("x3", 50, "casa", title="Carta igienica Foxy 18 rotoli")
assert [x.asin for x in engine.pick([a, b, c], cfgc, {}, limit=3)] == ["x3", "x2", "x1"]
assert engine.priority(b) == 2 and engine.priority(a) == 0
# deodoranti: persona -> cura_persona, ambienti -> casa
assert engine.parse_item(it("Nivea Deodorante Roll-on 48h Black & White", 3.0), "cura_persona")
assert not engine.parse_item(it("Air Wick Deodorante per ambienti spray 3 pezzi", 6.0), "cura_persona")
assert engine.parse_item(it("Air Wick Deodorante per ambienti spray 3 pezzi", 6.0), "casa")
# quasi identici: stessa marca+linea, titoli un po' diversi
k = lambda t: engine.title_key(mk("z", 50, "casa", title=t))
assert engine.same_product(k("Finish Ultimate Infinity Shine Pastiglie Lavastoviglie 60"), k("Finish Ultimate Plus Infinity Shine 90 Tabs"))
assert not engine.same_product(k("Borotalco Deodorante Spray Intensivo"), k("Borotalco Kit 3 Bagnodoccia Tripla Azione"))
assert not engine.same_product(k("Scottonelle Carta Igienica 18 Rotoli"), k("Lenor Profumatore Bucato Lavatrice"))
f1 = mk("f1", 60, "casa", title="Finish Ultimate Infinity Shine Pastiglie 60")
f2 = mk("f2", 58, "casa", title="Finish Ultimate Plus Infinity Shine 90")
o1 = mk("o1", 50, "casa", title="Lenor Ammorbidente 100 lavaggi")
assert [x.asin for x in engine.pick([f1, f2, o1], cfgc, {}, limit=3)] == ["o1", "f1"]
# non due offerte di fila della stessa marca, nemmeno fra un controllo e l'altro
m1, m2 = mk("m1", 60, "casa", title="Dixan Detersivo Lavatrice 100"), mk("m2", 59, "casa", title="Dixan Ammorbidente 80")
assert engine.pick([m1, m2], cfgc, {"deals_last_brand": "dixan"}, limit=2) == []
# elettrodomestici: solo super offerte (60%+), 1 al giorno
cfge = settings.load({})
assert cfge["categorie"]["elettrodomestici"]["max_giorno"] == 1 and settings.min_discount(cfge, "elettrodomestici") == 60
assert settings.min_discount(cfge, "casa") == 40
lav50, lav65, lav70 = (mk("w1", 50, "elettrodomestici", price=300), mk("w2", 65, "elettrodomestici", price=300),
                       mk("w3", 70, "elettrodomestici", price=400, title="Samsung Frigorifero Combinato"))
assert [x.asin for x in engine.pick([lav50, lav65, lav70], cfge, {}, limit=3)] == ["w3"]   # il 50% non passa, ne esce 1 solo
print("tutto ok")
