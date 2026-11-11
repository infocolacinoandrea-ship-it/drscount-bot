"""Decide quali offerte meritano un post."""
from __future__ import annotations

import config
from scraper import Offer


def is_home(o: Offer) -> bool:
    t = o.title.lower()
    return any(k in t for k in config.HOME_KEYWORDS)


def score(o: Offer) -> float:
    s = float(o.discount)
    if o.historic_low:
        s += 15
    if is_home(o):
        s += 12
    if o.rating:
        s += (o.rating - 4.0) * 20
    if o.reviews >= 1000:
        s += 5
    return s


def eligible(o: Offer) -> bool:
    return (
        o.discount >= config.MIN_DISCOUNT
        and (o.rating == 0 or o.rating >= config.MIN_RATING)
        and (o.reviews == 0 or o.reviews >= config.MIN_REVIEWS)
        and o.photo_url is not None
    )
