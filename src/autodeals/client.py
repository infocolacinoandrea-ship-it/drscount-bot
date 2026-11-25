"""Client minimo della Creators API di Amazon (credenziali v3.2, OAuth 2.0)."""
import os
import time

import requests

TOKEN_URL = "https://api.amazon.co.uk/auth/o2/token"   # v3.2 = Europa
API = "https://creatorsapi.amazon/catalog/v1"
PARTNER_TAG = os.getenv("PARTNER_TAG", "drscount06-21")
RESOURCES = ["images.primary.large", "itemInfo.title", "offersV2.listings.price",
             "offersV2.listings.merchantInfo", "offersV2.listings.availability"]
REVIEW_RESOURCES = ["customerReviews.count", "customerReviews.starRating"]


class CreatorsClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, pause: float = 1.1):
        self.cid = client_id or os.getenv("CREATORS_CLIENT_ID", "")
        self.sec = client_secret or os.getenv("CREATORS_CLIENT_SECRET", "")
        self.pause = pause
        self._token = ""
        self._exp = 0.0
        self._last = 0.0
        self.reviews = True       # prova a chiedere anche le recensioni; se l'API le rifiuta smette

    def token(self) -> str:
        if self._token and time.time() < self._exp - 60:
            return self._token
        r = requests.post(TOKEN_URL, json={"grant_type": "client_credentials", "client_id": self.cid,
                                           "client_secret": self.sec, "scope": "creatorsapi::default"},
                          timeout=30)
        r.raise_for_status()
        js = r.json()
        self._token, self._exp = js["access_token"], time.time() + int(js.get("expires_in", 3600))
        return self._token

    def search(self, keywords: str, index: str = "All", page: int = 1, min_saving: int | None = None) -> list[dict]:
        """Ritorna fino a 10 prodotti grezzi. Rispetta una pausa tra le chiamate."""
        wait = self.pause - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        body = {"keywords": keywords, "partnerTag": PARTNER_TAG, "itemCount": 10, "itemPage": page,
                "resources": RESOURCES + (REVIEW_RESOURCES if self.reviews else [])}
        if index and index != "All":
            body["searchIndex"] = index
        if min_saving:
            body["minSavingPercent"] = int(min_saving)
        for attempt in range(3):
            r = requests.post(f"{API}/searchItems", json=body, timeout=30, headers={
                "Authorization": f"Bearer {self.token()}", "Content-Type": "application/json",
                "x-marketplace": "www.amazon.it"})
            self._last = time.time()
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code == 400 and self.reviews:
                self.reviews = False
                print(f"[bot-offerte] recensioni non accettate: {r.text[:200]}")
                body["resources"] = RESOURCES
                continue
            if not r.ok:
                raise RuntimeError(f"SearchItems {r.status_code}: {r.text[:300]}")
            return (r.json().get("searchResult") or {}).get("items") or []
        raise RuntimeError("SearchItems: troppi errori")
