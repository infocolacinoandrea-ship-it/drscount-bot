"""Pubblicazione su Instagram con l'API ufficiale (Instagram API with Instagram Login)."""
from __future__ import annotations

import time

import requests

import config


def _check(r: requests.Response) -> dict:
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram: {data}")
    return data


def publish_image(image_url: str, caption: str = "", story: bool = False) -> str:
    base = f"{config.IG_API}/{config.IG_USER_ID}"
    tok = {"access_token": config.IG_TOKEN}
    data = {"image_url": image_url, **tok}
    if story:
        data["media_type"] = "STORIES"
    else:
        data["caption"] = caption
    container = _check(requests.post(f"{base}/media", data=data, timeout=60))["id"]

    # Instagram scarica l'immagine: si aspetta che il contenitore sia pronto
    for _ in range(20):
        st = _check(requests.get(f"{config.IG_API}/{container}",
                                 params={"fields": "status_code", **tok}, timeout=30))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram non è riuscito a elaborare l'immagine: {st}")
        time.sleep(3)

    res = _check(requests.post(f"{base}/media_publish", data={"creation_id": container, **tok}, timeout=60))
    return res["id"]


def permalink(media_id: str) -> str:
    try:
        return _check(requests.get(f"{config.IG_API}/{media_id}", params={
            "fields": "permalink", "access_token": config.IG_TOKEN}, timeout=30)).get("permalink", "")
    except Exception:
        return ""


def refresh_token() -> dict:
    """Allunga la validità del token (60 giorni). Va chiamata almeno una volta al mese."""
    return _check(requests.get("https://graph.instagram.com/refresh_access_token", params={
        "grant_type": "ig_refresh_token", "access_token": config.IG_TOKEN}, timeout=30))
