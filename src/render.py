"""Genera l'immagine del post Instagram (1080x1350, formato 4:5)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "logo.png"

W, H = 1080, 1350

# Palette presa dal logo del canale (verde banconote + oro monete)
DARK = (22, 52, 42)
GREEN = (30, 160, 90)
GOLD = (255, 193, 37)
CREAM = (247, 244, 236)
GREY = (140, 140, 140)
RED = (225, 45, 57)
WHITE = (255, 255, 255)


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def trim_white(img: Image.Image, tol: int = 18) -> Image.Image:
    """Taglia i bordi bianchi attorno al prodotto."""
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda v: 255 if v > tol else 0)
    box = diff.getbbox()
    return rgb.crop(box) if box else rgb


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return m


def fit_text(draw, text, weight, max_w, start, min_size=20):
    size = start
    while size > min_size:
        f = font(weight, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return font(weight, min_size)


def render_post(product_img: Image.Image, title: str, price: str, old_price: str,
                discount: int | None, historic_low: bool, out_path: Path) -> Path:
    canvas = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(canvas)

    # --- Header: logo + nome ---
    logo = Image.open(LOGO).convert("RGB").resize((120, 120), Image.LANCZOS)
    canvas.paste(logo, (60, 52), rounded_mask((120, 120), 60))
    d.ellipse((57, 49, 183, 175), outline=DARK, width=4)
    d.text((205, 62), "DR.SCOUNT", font=font("Bold", 54), fill=DARK)
    d.text((207, 128), "le offerte migliori, ogni giorno", font=font("Medium", 26), fill=GREEN)

    # --- Card prodotto ---
    card = (60, 215, W - 60, 925)
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((card[0], card[1] + 14, card[2], card[3] + 14), 48, fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    canvas.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), shadow)
    d.rounded_rectangle(card, 48, fill=WHITE)

    prod = trim_white(product_img)
    box_w, box_h = card[2] - card[0] - 120, card[3] - card[1] - 120
    scale = min(box_w / prod.width, box_h / prod.height)
    prod = prod.resize((int(prod.width * scale), int(prod.height * scale)), Image.LANCZOS)
    px = card[0] + (card[2] - card[0] - prod.width) // 2
    py = card[1] + (card[3] - card[1] - prod.height) // 2
    canvas.paste(prod, (px, py))

    # --- Badge sconto (cerchio oro in alto a destra) ---
    if discount:
        cx, cy, r = W - 120, 225, 105
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED, outline=WHITE, width=8)
        d.text((cx, cy - 4), f"-{discount}%", font=font("Bold", 58), fill=WHITE, anchor="mm")

    # --- Nastro "minimo storico" ---
    if historic_low:
        label = "MINIMO STORICO"
        f = font("Bold", 30)
        tw = d.textlength(label, font=f)
        x0, y0 = card[0] + 36, card[1] + 34
        d.rounded_rectangle((x0, y0, x0 + tw + 48, y0 + 56), 28, fill=GOLD)
        d.text((x0 + 24, y0 + 28), label, font=f, fill=DARK, anchor="lm")

    # --- Titolo breve ---
    f_title = fit_text(d, title, "Medium", W - 140, 40, 26)
    d.text((W // 2, 975), title, font=f_title, fill=DARK, anchor="mm")

    # --- Prezzi ---
    f_new = font("Bold", 140)
    f_old = font("Medium", 58)
    new_w = d.textlength(price, font=f_new)
    old_w = d.textlength(old_price, font=f_old)
    gap = 36
    total = new_w + gap + old_w
    x = (W - total) / 2
    base_y = 1085
    d.text((x, base_y), price, font=f_new, fill=GREEN, anchor="lm")
    ox = x + new_w + gap
    d.text((ox, base_y + 20), old_price, font=f_old, fill=GREY, anchor="lm")
    d.line((ox - 4, base_y + 22, ox + old_w + 4, base_y + 22), fill=RED, width=6)

    # --- Fascia CTA ---
    d.rectangle((0, H - 120, W, H), fill=DARK)
    cta = "OFFERTA NEL LINK IN BIO"
    f_cta = font("Bold", 46)
    cw = d.textlength(cta, font=f_cta)
    tx = (W - cw - 70) / 2
    d.text((tx, H - 60), cta, font=f_cta, fill=WHITE, anchor="lm")
    # freccia verso l'alto disegnata (le emoji non escono bene nei font)
    ax, ay = tx + cw + 40, H - 60
    d.polygon([(ax, ay - 26), (ax - 22, ay + 2), (ax - 8, ay + 2), (ax - 8, ay + 26),
               (ax + 8, ay + 26), (ax + 8, ay + 2), (ax + 22, ay + 2)], fill=GOLD)

    stamp = f"Prezzo rilevato il {dt.date.today():%d/%m} · può variare"
    d.text((W // 2, H - 155), stamp, font=font("Regular", 22), fill=GREY, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=92)
    return out_path


SW, SH = 1080, 1920


def render_story(post_path: Path, out_path: Path) -> Path:
    """Storia 1080x1920: il post al centro su sfondo del brand, con invito al link in bio."""
    post = Image.open(post_path).convert("RGB")
    canvas = Image.new("RGB", (SW, SH), DARK)
    # sfondo: il post sfocato e scurito, per un effetto "ricondiviso"
    bg = post.resize((SW, int(post.height * SW / post.width)), Image.LANCZOS)
    bg = bg.resize((int(bg.width * SH / bg.height * 1.0) or SW, SH), Image.LANCZOS) if bg.height < SH else bg
    bg = bg.crop(((bg.width - SW) // 2, 0, (bg.width - SW) // 2 + SW, SH)).filter(ImageFilter.GaussianBlur(40))
    canvas.paste(Image.blend(bg, Image.new("RGB", (SW, SH), DARK), 0.55), (0, 0))
    d = ImageDraw.Draw(canvas)

    d.text((SW // 2, 200), "NUOVA OFFERTA", font=font("Bold", 84), fill=GOLD, anchor="mm")
    d.text((SW // 2, 285), "appena pubblicata sul profilo", font=font("Medium", 40), fill=WHITE, anchor="mm")

    w = 900
    h = int(post.height * w / post.width)
    card = post.resize((w, h), Image.LANCZOS)
    x, y = (SW - w) // 2, 380
    sh = Image.new("L", (SW, SH), 0)
    ImageDraw.Draw(sh).rounded_rectangle((x, y + 18, x + w, y + h + 18), 40, fill=120)
    canvas.paste(Image.new("RGB", (SW, SH), (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(25)))
    canvas.paste(card, (x, y), rounded_mask((w, h), 40))

    by = y + h + 120
    label = "TROVI IL LINK IN BIO"
    f = font("Bold", 58)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle(((SW - tw) / 2 - 50, by - 60, (SW + tw) / 2 + 50, by + 60), 60, fill=GOLD)
    d.text((SW // 2, by), label, font=f, fill=DARK, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=90)
    return out_path
