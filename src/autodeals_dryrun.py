"""Prova a secco dell'autodeals: cerca offerte vere e le mostra, senza pubblicare niente."""
import sys

from autodeals import engine, settings
from autodeals.categories import CATEGORIES
from autodeals.client import CreatorsClient


def main() -> int:
    cfg = settings.load({})
    state: dict = {}
    client = CreatorsClient()
    found = engine.scan(client, cfg, state, per_category=2)
    print(f"\nTrovati {len(found)} prodotti con sconto, di cui {sum(engine.passes(d, cfg) for d in found)} "
          f"passano i filtri (sconto {cfg['sconto_min']}-{cfg['sconto_max']}%, solo Amazon={cfg['solo_amazon']})\n")
    for cid, cat in CATEGORIES.items():
        mine = [d for d in found if d.category == cid]
        ok = [d for d in mine if engine.passes(d, cfg)]
        print(f"== {cat['label']}: {len(mine)} con sconto, {len(ok)} validi")
        for d in sorted(ok, key=lambda x: -x.discount)[:3]:
            print(f"   -{d.discount}% {d.price_txt} (era {d.old_price_txt}, {d.basis}) {d.seller} | {d.title}")
    chosen = engine.pick(found, cfg, state, limit=cfg["max_al_giorno"])
    print(f"\nSelezione con quote giornaliere: {len(chosen)} offerte")
    for d in chosen:
        print(f"   [{d.category}] -{d.discount}% {d.price_txt} | {d.title} | {d.link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
