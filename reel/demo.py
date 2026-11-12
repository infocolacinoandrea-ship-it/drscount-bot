"""Prova locale: genera i due reel di esempio a partire dai post già pubblicati.

    python -m reel.demo            # crea reel/examples/reel_scottex.mp4 e reel_adidas.mp4
"""
from pathlib import Path

from PIL import Image, ImageDraw

from .render_reel import ROOT, WHITE, render_reel


def product_from_post(post_jpg: Path) -> Image.Image:
    """Solo per la demo: ritaglia il prodotto da un post 1080x1350 già generato
    (nel bot si usa invece la foto originale dell'offerta)."""
    im = Image.open(post_jpg).convert("RGB")
    d = ImageDraw.Draw(im)
    d.ellipse((842, 107, 1078, 343), fill=WHITE)       # copre il badge sconto
    d.rounded_rectangle((90, 240, 420, 312), 30, fill=WHITE)  # copre "MINIMO STORICO"
    return im.crop((90, 240, 990, 895))


EXAMPLES = [
    ("scottex", "31004.jpg", "Scottex Carta da Cucina 21 rotoli", "14,89€", "29,99€", 51, True),
    ("adidas", "31002.jpg", "adidas Kids Scarpe Tensaur Sport", "18,28€", "38,00€", 52, False),
]

if __name__ == "__main__":
    out = ROOT / "reel" / "examples"
    for slug, post, title, price, old, disc, low in EXAMPLES:
        p = render_reel(product_from_post(ROOT / "posts" / post), title, price, old, disc, low,
                        out / f"reel_{slug}.mp4", cover_path=out / f"reel_{slug}_cover.jpg")
        print("creato", p)
