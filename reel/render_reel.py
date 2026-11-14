"""Reel Dr.Scount 1080x1920 (stile "B", senza voce): jingle + effetti sonori.

Scena 1 - "schermo-prezzo" (0 -> ~3.3 s), fondo rosso/arancio con raggiera che gira:
  0.00 s  card bianca del prodotto + stella gialla + "SOLO" + prezzo nuovo esplodono insieme
          (pop forte, "ding" e flash bianco)
  0.00 s  insieme compare anche "invece di <prezzo vecchio>", già barrato
Transizione (3.27 -> 3.59 s): lo schermo-prezzo si rimpicciolisce dentro la card del post.
Scena 2 - grafica del post (3.27 s -> fine), fondo crema con raggiera dorata:
  3.27 s  card prodotto (+ nastro MINIMO STORICO) e titolo esplodono insieme;
          prezzo nuovo/vecchio già al loro posto sulla stella
  4.35 s  badge "-XX%" si gonfia
  5.75 s  pillola "OFFERTA NEL LINK IN BIO" compare con un ingrandimento
  ~8.45 s fine (accordo "ta-dan" del jingle)

Uso:
    from reel.render_reel import render_reel
    render_reel(product_img, "Scottex Carta da Cucina", "14,89€", "29,99€", 51, True, Path("out.mp4"))
"""
from __future__ import annotations

import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import music

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "logo.png"

W, H, FPS = 1080, 1920, 30
SR = music.SR

DARK = (22, 52, 42)
GREEN = (30, 160, 90)
GOLD = (255, 193, 37)
CREAM = (247, 244, 236)
GREY = (140, 140, 140)
RED = (225, 45, 57)
WHITE = (255, 255, 255)

# Tempi (secondi): (inizio, durata in cui l'elemento resta "gonfio")
CUES = {
    "new": (0.12, 1.70),    # prezzo nuovo + prodotto (scena 1)
    "old": (0.00, 1.70),    # "invece di ..." già barrato, insieme al prezzo nuovo (scena 1)
    "title": (3.27, 0.90),  # card + titolo (scena 2), coincide con il cambio scena
    "badge": (4.35, 1.20),  # badge sconto
    "cta": (5.75, 1.10),    # OFFERTA NEL LINK IN BIO
}
T_SWITCH = 3.27   # cambio scena
TRANSITION = 0.32
TOTAL = CUES["cta"][0] + CUES["cta"][1] + 1.6        # = 8.45 s


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


# ------------------------------------------------------------------ utilità grafiche
def trim_white(img: Image.Image, tol: int = 18) -> Image.Image:
    rgb = img.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, WHITE)).convert("L")
    box = diff.point(lambda v: 255 if v > tol else 0).getbbox()
    return rgb.crop(box) if box else rgb


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return m


def sprite_text(text, f, fill, stroke=0, stroke_fill=None, pad=20):
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def rays(size, n, color, alpha):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = a0 + math.pi / n
        d.polygon([(c, c), (c + c * 1.5 * math.cos(a0), c + c * 1.5 * math.sin(a0)),
                   (c + c * 1.5 * math.cos(a1), c + c * 1.5 * math.sin(a1))], fill=color + (alpha,))
    return im


def starburst(r_out, r_in, n, fill, outline):
    s = int(r_out * 2 + 20)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / n
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    ImageDraw.Draw(im).polygon(pts, fill=fill, outline=outline, width=8)
    return im


# ------------------------------------------------------------------ animazione
def ease_out_back(x, k=2.2):
    x -= 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def punch(t, start, dur, peak=1.4):
    """Scala di un elemento: esplode (0.14 s), resta gonfio e fermo per `dur`,
    poi si sgonfia con rimbalzo (0.35 s) e resta fermo. Niente tremolii."""
    if t < start:
        return 0.0
    u = t - start
    if u < 0.14:
        return peak * ease_out_back(u / 0.14, 1.6)
    if u < dur:
        return peak
    v = u - dur
    if v < 0.35:
        return 1 + (peak - 1) * (1 - ease_out_back(v / 0.35, 1.8))
    return 1.0


def paste_scaled(canvas, spr, center, scale, angle=0.0):
    if scale <= 0.02:
        return
    w, h = max(1, int(spr.width * scale)), max(1, int(spr.height * scale))
    s = spr.resize((w, h), Image.BILINEAR)
    if angle:
        s = s.rotate(angle, resample=Image.BILINEAR, expand=True)
    canvas.alpha_composite(s, (int(center[0] - s.width / 2), int(center[1] - s.height / 2)))


# ------------------------------------------------------------------ audio
def sfx_pop(big=False):
    n = int(SR * (0.22 if big else 0.14))
    t = np.arange(n) / SR
    f = np.linspace(900 if big else 1200, 180, n)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (14 if big else 22))
    noise = np.random.randn(n) * np.exp(-t * 60) * 0.25
    return ((w + noise) * (0.55 if big else 0.4)).astype(np.float32)


def sfx_ding():
    n = int(SR * 1.1)
    t = np.arange(n) / SR
    w = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1568, .5), (2093, .35), (3136, .15)])
    return (w * np.exp(-t * 4.5) * 0.35).astype(np.float32)


def build_audio(path: Path):
    np.random.seed(11)
    n = int(TOTAL * SR)
    mix = music.jingle(TOTAL)[:n] * 0.55
    mix = np.pad(mix, (0, n - len(mix)))

    def add(x, at):
        i = int(at * SR)
        if i < n:
            mix[i:i + len(x)] += x[: n - i]
    add(sfx_pop(big=True), CUES["new"][0])
    add(sfx_ding(), CUES["new"][0] + 0.25)
    for key in ("title", "badge", "cta"):
        add(sfx_pop(), CUES[key][0])
    # saturazione morbida + guadagno (~ -14.5 LUFS, livello consigliato per Instagram)
    mix = np.tanh(mix * 1.4) * 0.95
    mix = np.clip(mix * 10 ** (5.5 / 20), -0.95, 0.95)
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ grafica
class Sprites:
    def __init__(self, product: Image.Image, title: str, price: str, old_price: str,
                 discount: int | None, historic_low: bool):
        tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        product = trim_white(product)
        self.logo = Image.open(LOGO).convert("RGB").resize((140, 140), Image.LANCZOS)

        # card del post
        self.card = c = (60, 370, W - 60, 1050)
        spr = Image.new("RGBA", (c[2] - c[0] + 80, c[3] - c[1] + 80), (0, 0, 0, 0))
        sh = Image.new("L", spr.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle((40, 54, spr.width - 40, spr.height - 26), 48, fill=80)
        spr.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(20)))
        ImageDraw.Draw(spr).rounded_rectangle((40, 40, spr.width - 40, spr.height - 40), 48, fill=WHITE)
        sc = min((c[2] - c[0] - 140) / product.width, (c[3] - c[1] - 150) / product.height)
        p = product.resize((int(product.width * sc), int(product.height * sc)), Image.LANCZOS)
        spr.paste(p, ((spr.width - p.width) // 2, (spr.height - p.height) // 2 + 20))
        self.card_spr, self.card_c = spr, ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)

        self.pill = None
        if historic_low:
            t = sprite_text("MINIMO STORICO", font("Bold", 34), DARK, pad=0)
            pl = Image.new("RGBA", (t.width + 56, 66), (0, 0, 0, 0))
            ImageDraw.Draw(pl).rounded_rectangle((0, 0, pl.width - 1, 65), 33, fill=GOLD)
            pl.alpha_composite(t, (28, (66 - t.height) // 2))
            self.pill = pl

        self.badge = None
        if discount:
            br = 120
            b = Image.new("RGBA", (2 * br + 20, 2 * br + 20), (0, 0, 0, 0))
            ImageDraw.Draw(b).ellipse((10, 10, 2 * br + 10, 2 * br + 10), fill=RED, outline=WHITE, width=9)
            bt = sprite_text(f"-{discount}%", font("Bold", 68), WHITE, pad=0)
            b.alpha_composite(bt, ((b.width - bt.width) // 2, (b.height - bt.height) // 2 - 4))
            self.badge = b

        tf = font("Bold", 50)
        while tmp.textlength(title, font=tf) > W - 160 and tf.size > 30:
            tf = font("Bold", tf.size - 2)
        self.title = sprite_text(title, tf, DARK)
        self.title_peak = min(1.25, (W - 30) / self.title.width)   # non esce mai dai bordi

        self.new = sprite_text(price, font("Bold", 165), GREEN, stroke=6, stroke_fill=WHITE)
        self.old = sprite_text(old_price, font("Medium", 66), GREY)
        tot = self.new.width + 30 + self.old.width - 40
        self.new_c = ((W - tot) / 2 + self.new.width / 2, 1365)
        self.old_c = ((W - tot) / 2 + self.new.width + 30 + self.old.width / 2 - 40, 1383)
        self.star = starburst(300, 235, 20, GOLD + (255,), DARK).resize((900, 330), Image.LANCZOS)
        self.bg_rays = rays(2600, 24, GOLD, 55)

        cf = font("Bold", 46)
        ct = "OFFERTA NEL LINK IN BIO"
        cw = tmp.textlength(ct, font=cf)
        cta = Image.new("RGBA", (int(cw) + 150, 104), (0, 0, 0, 0))
        d = ImageDraw.Draw(cta)
        d.rounded_rectangle((0, 0, cta.width - 1, 103), 52, fill=DARK)
        d.text((44, 52), ct, font=cf, fill=WHITE, anchor="lm")
        ax, ay = 44 + cw + 44, 52
        d.polygon([(ax, ay - 26), (ax - 22, ay + 2), (ax - 8, ay + 2), (ax - 8, ay + 26),
                   (ax + 8, ay + 26), (ax + 8, ay + 2), (ax + 22, ay + 2)], fill=GOLD)
        self.cta, self.cta_c = cta, (W / 2, 1585)

        # scena 1: schermo-prezzo
        self.b_rays = rays(2600, 20, GOLD, 120)
        self.b_star = starburst(400, 320, 22, GOLD + (255,), DARK)
        self.b_solo = sprite_text("SOLO", font("Bold", 120), WHITE, stroke=10, stroke_fill=DARK)
        f = font("Bold", 250)
        while tmp.textlength(price, font=f) > 700:
            f = font("Bold", f.size - 6)
        self.b_new = sprite_text(price, f, RED, stroke=12, stroke_fill=WHITE)
        fo = font("Bold", 64)
        old_txt = f"invece di {old_price}"
        self.b_old = sprite_text(old_txt, fo, WHITE, stroke=6, stroke_fill=DARK)
        self.b_old_k = tmp.textlength("invece di ", font=fo) / tmp.textlength(old_txt, font=fo)
        sc2 = min(560 / product.width, 430 / product.height)
        pp = product.resize((int(product.width * sc2), int(product.height * sc2)), Image.LANCZOS)
        bp = Image.new("RGBA", (pp.width + 100, pp.height + 100), (0, 0, 0, 0))
        ImageDraw.Draw(bp).rounded_rectangle((0, 0, bp.width - 1, bp.height - 1), 44, fill=WHITE,
                                             outline=DARK, width=8)
        bp.paste(pp, (50, 50))
        self.b_prod = bp


def draw_header(c, s: Sprites):
    d = ImageDraw.Draw(c)
    c.paste(s.logo, (60, 210), rounded_mask((140, 140), 70))
    d.ellipse((57, 207, 203, 353), outline=DARK, width=4)
    d.text((228, 225), "DR.SCOUNT", font=font("Bold", 58), fill=DARK)
    d.text((230, 297), "le offerte migliori, ogni giorno", font=font("Medium", 28), fill=GREEN)


def strike(c, center, spr, scale):
    hw = spr.width / 2 * scale
    x0 = center[0] - hw + 14 * scale
    x1 = x0 + (2 * hw - 28 * scale)
    ImageDraw.Draw(c).line((x0, center[1] + 6 * scale, x1, center[1] - 2 * scale),
                           fill=RED, width=max(4, int(8 * scale)))


def post_scene(tt, s: Sprites):
    """Scena 2: grafica del post."""
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    r = s.bg_rays.rotate(tt * 12, resample=Image.BILINEAR)
    c.alpha_composite(r, (int(W / 2 - r.width / 2), int(900 - r.height / 2)))
    draw_header(c, s)
    t0 = T_SWITCH
    cs = ease_out_back(min(1, max(0, (tt - t0) / 0.35)), 1.4) if tt >= t0 else 0
    paste_scaled(c, s.card_spr, s.card_c, cs)
    if s.pill is not None and tt > t0 + 0.2:
        paste_scaled(c, s.pill, (s.card[0] + 36 + s.pill.width / 2, s.card[1] + 73),
                     punch(tt, t0 + 0.2, 0.05, 1.15))
    paste_scaled(c, s.star, (W / 2, s.new_c[1]), 1.0)
    paste_scaled(c, s.old, s.old_c, 1.0)
    strike(c, s.old_c, s.old, 1.0)
    paste_scaled(c, s.new, s.new_c, 1.0)
    st, du = CUES["title"]
    paste_scaled(c, s.title, (W / 2, 1140), punch(tt, st, du, s.title_peak))
    if s.badge is not None:
        st, du = CUES["badge"]
        paste_scaled(c, s.badge, (W - 175, s.card[1] + 20), punch(tt, st, du, 1.45),
                     angle=-8)
    st, du = CUES["cta"]
    if tt >= st:
        paste_scaled(c, s.cta, s.cta_c, punch(tt, st, du, 1.25))
    return c


def price_scene(tt, s: Sprites):
    """Scena 1: prodotto + prezzo gigante su fondo rosso."""
    c = Image.new("RGBA", (W, H), RED + (255,))
    r = s.b_rays.rotate(tt * 25, resample=Image.BILINEAR)
    c.alpha_composite(r, (int(W / 2 - r.width / 2), int(900 - r.height / 2)))
    st, du = CUES["new"]
    paste_scaled(c, s.b_prod, (W / 2, 590), punch(tt, st - 0.12, du, 1.12),
                 angle=-4)
    paste_scaled(c, s.b_star, (W / 2, 1250), punch(tt, st - 0.12, du, 1.0))
    paste_scaled(c, s.b_solo, (W / 2, 1060), punch(tt, st - 0.12, 0.45, 1.25), angle=-6)
    paste_scaled(c, s.b_new, (W / 2, 1240), punch(tt, st, du, 1.2),
                 angle=-4)
    sto, duo = CUES["old"]
    so = punch(tt, sto, duo, 1.3)
    oc = (W / 2, 1490)
    paste_scaled(c, s.b_old, oc, so)
    if tt >= sto:   # la barra c'è già da subito
        k = 1
        tw = (s.b_old.width - 40) * so
        x0 = oc[0] - tw / 2 + tw * s.b_old_k - 6
        x1 = x0 + (oc[0] + tw / 2 + 6 - x0) * k
        ImageDraw.Draw(c).line((x0, oc[1] + 10, x1, oc[1] - 4), fill=RED, width=12)
    return c


def frame(tt, s: Sprites, rng: random.Random) -> Image.Image:
    if tt < T_SWITCH:
        img = price_scene(tt, s)
    else:
        img = post_scene(tt, s)
        u = (tt - T_SWITCH) / TRANSITION
        if u < 1:   # lo schermo-prezzo si rimpicciolisce dentro la card del post
            ps = price_scene(T_SWITCH, s)
            k = 1 - (1 - u) ** 3
            ps.putalpha(int(255 * (1 - k)))
            paste_scaled(img, ps, (W / 2 + (s.card_c[0] - W / 2) * k, H / 2 + (s.card_c[1] - H / 2) * k),
                         1 - 0.85 * k)
    img = img.convert("RGB")
    u = tt - CUES["new"][0]
    if 0 <= u < 0.1:    # flash
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.4 * (1 - u / 0.1))
    return img


# ------------------------------------------------------------------ API
def render_reel(product_img: Image.Image, title: str, price: str, old_price: str,
                discount: int | None, historic_low: bool, out_path: Path,
                cover_path: Path | None = None) -> Path:
    """Genera il reel MP4 (H.264 + AAC, 1080x1920, 30 fps, ~8.5 s).
    price/old_price sono stringhe già formattate, es. "14,89€" (come in scraper.Offer).
    Se cover_path è indicato salva anche la copertina JPG (frame a 1.0 s)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = out_path.parent / f".{out_path.stem}_tmp"
    work.mkdir(exist_ok=True)
    s = Sprites(product_img, title, price, old_price, discount, historic_low)
    rng = random.Random(5)
    ff = ffmpeg_bin()

    audio = work / "audio.wav"
    build_audio(audio)

    video = work / "video.mp4"
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(video)],
                            stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        proc.stdin.write(frame(i / FPS, s, rng).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg: codifica video non riuscita")

    part = out_path.with_name(out_path.stem + ".part.mp4")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-shortest", "-movflags", "+faststart", str(part)], check=True)
    part.replace(out_path)

    if cover_path:
        frame(1.0, s, random.Random(0)).save(cover_path, "JPEG", quality=90)
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    return out_path
