"""Immagine dell'offerta in stile autodeals, con il logo Dr.Scount (1080x1350, adatta a Telegram)."""
from __future__ import annotations

from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

from render import (CREAM, DARK, GOLD, GREEN, GREY, H, LOGO, RED, W, WHITE, fit_text, font, rounded_mask,
                    trim_white)


def download(url: str) -> Image.Image:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    import io
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def render_deal(product_img: Image.Image, title: str, price: str, old_price: str, discount: int,
                category_label: str, out_path: Path, was_price: bool = False) -> Path:
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)

    # intestazione: logo + nome + categoria
    logo = Image.open(LOGO).convert("RGB").resize((110, 110), Image.LANCZOS)
    canvas.paste(logo, (60, 48), rounded_mask((110, 110), 55))
    d.ellipse((57, 45, 173, 161), outline=DARK, width=4)
    d.text((192, 60), "DR.SCOUNT", font=font("Bold", 52), fill=DARK)
    d.text((194, 124), category_label.upper(), font=font("Medium", 26), fill=GREEN)

    # card prodotto con ombra
    card = (60, 200, W - 60, 900)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((card[0], card[1] + 14, card[2], card[3] + 14), 48, fill=70)
    canvas.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(22)))
    d.rounded_rectangle(card, 48, fill=WHITE)
    prod = trim_white(product_img)
    bw, bh = card[2] - card[0] - 110, card[3] - card[1] - 110
    sc = min(bw / prod.width, bh / prod.height)
    prod = prod.resize((int(prod.width * sc), int(prod.height * sc)), Image.LANCZOS)
    canvas.paste(prod, (card[0] + (card[2] - card[0] - prod.width) // 2,
                        card[1] + (card[3] - card[1] - prod.height) // 2))

    # badge sconto
    cx, cy, r = W - 125, 215, 108
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED, outline=WHITE, width=8)
    d.text((cx, cy - 4), f"-{discount}%", font=font("Bold", 60), fill=WHITE, anchor="mm")

    # titolo
    d.text((W // 2, 950), title, font=fit_text(d, title, "Medium", W - 140, 42, 26), fill=DARK, anchor="mm")

    # prezzi (se non c'è un vero "prezzo precedente" si scrive "invece di")
    f_new, f_old = font("Bold", 140), font("Medium", 58)
    nw, ow, gap = d.textlength(price, font=f_new), d.textlength(old_price, font=f_old), 36
    x, y = (W - (nw + gap + ow)) / 2, 1065
    d.text((x, y), price, font=f_new, fill=GREEN, anchor="lm")
    ox = x + nw + gap
    d.text((ox, y + 20), old_price, font=f_old, fill=GREY, anchor="lm")
    d.line((ox - 4, y + 22, ox + ow + 4, y + 22), fill=RED, width=6)

    # fascia in basso
    d.rectangle((0, H - 120, W, H), fill=DARK)
    d.text((W // 2, H - 60), "TOCCA IL PULSANTE E VAI ALL'OFFERTA", font=fit_text(d, "TOCCA IL PULSANTE E VAI ALL'OFFERTA", "Bold", W - 80, 42, 24),
           fill=WHITE, anchor="mm")
    d.text((W // 2, H - 150), "Prezzo rilevato su Amazon · può variare", font=font("Regular", 22), fill=GREY, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=92)
    return out_path
