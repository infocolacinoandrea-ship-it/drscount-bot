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


def publish_video(video_url: str, caption: str = "", story: bool = False, cover_url: str = "") -> str:
    """Pubblica un reel (o una storia video). Instagram elabora il video: si aspetta FINISHED."""
    base = f"{config.IG_API}/{config.IG_USER_ID}"
    tok = {"access_token": config.IG_TOKEN}
    data = {"video_url": video_url, **tok}
    if story:
        data["media_type"] = "STORIES"
    else:
        data.update(media_type="REELS", caption=caption, share_to_feed="true")
        if cover_url:
            data["cover_url"] = cover_url
    container = _check(requests.post(f"{base}/media", data=data, timeout=60))["id"]
    for _ in range(60):  # fino a ~5 minuti
        time.sleep(5)
        st = _check(requests.get(f"{config.IG_API}/{container}",
                                 params={"fields": "status_code,status", **tok}, timeout=30))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram non è riuscito a elaborare il video: {st}")
    else:
        raise RuntimeError("Instagram ci mette troppo a elaborare il video")
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


def publishing_room() -> int:
    """Quanti contenuti si possono ancora pubblicare nelle 24 ore (limite di Instagram)."""
    try:
        d = _check(requests.get(f"{config.IG_API}/{config.IG_USER_ID}/content_publishing_limit", params={
            "fields": "quota_usage,config", "access_token": config.IG_TOKEN}, timeout=30))["data"][0]
        return int(d["config"]["quota_total"]) - int(d["quota_usage"])
    except Exception:
        return 99  # se non riesco a leggerlo, non blocco
