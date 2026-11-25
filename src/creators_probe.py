"""Prova della Creators API di Amazon: ottiene il token e fa una ricerca.
Stampa lo stato e la struttura della risposta (mai le credenziali né il token)."""
import json
import os
import sys

import requests

TOKEN_URL = "https://api.amazon.co.uk/auth/o2/token"      # credenziali v3.2 = Europa
API = "https://creatorsapi.amazon/catalog/v1"


def main() -> int:
    cid = os.getenv("CREATORS_CLIENT_ID", "")
    sec = os.getenv("CREATORS_CLIENT_SECRET", "")
    ver = os.getenv("CREATORS_VERSION", "")
    print(f"Secret presenti: id={bool(cid)} secret={bool(sec)} version={ver or '-'}")
    if not (cid and sec):
        print("Mancano i Secret CREATORS_CLIENT_ID / CREATORS_CLIENT_SECRET su GitHub.")
        return 1
    r = requests.post(TOKEN_URL, json={"grant_type": "client_credentials", "client_id": cid,
                                       "client_secret": sec, "scope": "creatorsapi::default"}, timeout=30)
    print("Token:", r.status_code, "" if r.ok else r.text[:300])
    if not r.ok:
        return 1
    token = r.json()["access_token"]
    hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "x-marketplace": "www.amazon.it"}
    res = ["images.primary.large", "itemInfo.title", "offersV2.listings.price",
           "offersV2.listings.merchantInfo", "offersV2.listings.availability"]
    tests = {
        "A: risorse prezzo+foto": {"keywords": os.getenv("PROBE_KEYWORDS", "detersivo lavatrice"),
                                   "partnerTag": "drscount06-21", "itemCount": 3, "resources": res},
        "B: con sconto minimo 30%": {"keywords": "detersivo lavatrice", "partnerTag": "drscount06-21",
                                     "itemCount": 3, "resources": res, "minSavingPercent": 30},
        "C: recensioni": {"keywords": "detersivo lavatrice", "partnerTag": "drscount06-21", "itemCount": 1,
                          "resources": ["itemInfo.title", "customerReviews.starRating", "customerReviews.count"]},
    }
    s = None
    for name, body in tests.items():
        s = requests.post(f"{API}/searchItems", json=body, timeout=30, headers=hdr)
        print(f"\n=== {name}: HTTP {s.status_code}")
        try:
            js = s.json()
            items = js.get("searchResult", {}).get("items")
            if items:
                print(json.dumps(items[0], indent=1, ensure_ascii=False)[:3500])
                print("n. prodotti:", len(items), "| totale:", js["searchResult"].get("totalResultCount"))
            else:
                print(json.dumps(js, indent=1, ensure_ascii=False)[:1200])
        except ValueError:
            print(s.text[:1200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
