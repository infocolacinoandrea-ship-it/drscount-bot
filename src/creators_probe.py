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
    body = {"keywords": os.getenv("PROBE_KEYWORDS", "detersivo lavatrice"), "partnerTag": "drscount06-21",
            "itemCount": 3}
    s = requests.post(f"{API}/searchItems", json=body, timeout=30,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                               "x-marketplace": "www.amazon.it"})
    print("SearchItems:", s.status_code)
    try:
        print(json.dumps(s.json(), indent=1, ensure_ascii=False)[:6000])
    except ValueError:
        print(s.text[:1500])
    return 0 if s.ok else 1


if __name__ == "__main__":
    sys.exit(main())
