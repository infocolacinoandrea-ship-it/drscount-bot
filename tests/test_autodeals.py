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


def mk(asin, pct, cat, seller="Amazon", basis="WAS_PRICE", price=20.0):
    return engine.Deal(asin, "t", price, price * 100 / (100 - pct), pct, basis, seller, "u", cat, "l")


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
assert [x.asin for x in got] == ["e1", "c1", "c2"], [x.asin for x in got]   # 1 elettrodomestico, tetto 3

# già pubblicati oggi + doppioni recenti
day = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).strftime("%Y-%m-%d")
st = {"deals_daily": {day: {"elettrodomestici": 1}}, "deals_seen": {"c1": dt.datetime.now(dt.timezone.utc).isoformat()}}
got = engine.pick(cands, cfg, st, limit=10)
assert [x.asin for x in got] == ["c2", "c3"], [x.asin for x in got]       # e* esaurito, c1 già visto
# categoria spenta
cfg["categorie"]["casa"]["attiva"] = False
assert engine.pick(cands, cfg, {}, limit=10)[0].category == "elettrodomestici"
print("tutto ok")
