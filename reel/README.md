# Reel Dr.Scount (stile "B", senza voce)

Genera per ogni offerta un reel verticale **1080×1920, 30 fps, ~8,5 s**, con H.264 + AAC 48 kHz a circa −14,5 LUFS.
È identico ai reel di prova `reel_scottex_B_muto.mp4` e `reel_adidas_B_muto.mp4`, e qui sotto `examples/` ci sono due esempi già generati con questo codice.

## File

| File | Cosa contiene |
|---|---|
| `reel/render_reel.py` | Tutto il generatore: grafica, animazioni, tempi, effetti sonori e codifica. La funzione da chiamare è `render_reel(...)`. |
| `reel/music.py` | Il jingle, sintetizzato in codice: è originale e senza copyright, quindi non serve nessun file audio. |
| `reel/demo.py` | La prova locale, che rigenera gli esempi partendo dai post in `posts/`. |
| `reel/requirements.txt` | Le librerie Python aggiuntive. |
| `reel/examples/` | Gli esempi già generati: due reel MP4 e le loro copertine JPG. |

**Risorse usate (già nel repo, non duplicate):**
- `assets/fonts/Poppins-Bold.ttf`, `assets/fonts/Poppins-Medium.ttf`: il font, lo stesso dei post.
- `assets/logo.png`: il logo nell'intestazione della scena 2.

Non ci sono immagini di sfondo: raggiere, stelle, card e pillole sono disegnate in codice.

## Dipendenze

```
pip install -r requirements.txt -r reel/requirements.txt
```
- **Pillow**: è già tra i requisiti del bot.
- **numpy** e **scipy**: servono per il jingle e gli effetti.
- **imageio-ffmpeg**: contiene un ffmpeg già pronto, quindi sul runner GitHub non serve installare ffmpeg con apt. Se però ffmpeg c'è già nel sistema, viene usato quello solo quando imageio-ffmpeg manca.

Python 3.10 o superiore.

## Prova

Dalla cartella principale del repo:

```
python -m reel.demo
```

Il comando crea `reel/examples/reel_scottex.mp4`, `reel_adidas.mp4` e le copertine.
Ogni reel richiede circa 75 secondi di elaborazione su una CPU come quella dei runner GitHub.

## Dati in ingresso (per ogni reel)

```python
from pathlib import Path
from reel.render_reel import render_reel

render_reel(
    product_img,        # PIL.Image: foto originale del prodotto (quella di o.photo_url)
    title,              # str: titolo breve, es. o.short_title; si rimpicciolisce se è troppo lungo
    price,              # str già formattata, es. "14,89€"  (= o.price)
    old_price,          # str già formattata, es. "29,99€"  (= o.old_price)
    discount,           # int, es. 51 (= o.discount); con None il badge non compare
    historic_low,       # bool: mostra il nastro "MINIMO STORICO" (= o.historic_low)
    Path("posts/31004_reel.mp4"),        # file di uscita
    cover_path=Path("posts/31004_reel.jpg"),  # facoltativo: copertina, cioè il frame a 1,0 s
)
```

Sono esattamente i campi di `scraper.Offer`. Il bordo bianco della foto viene tagliato da solo.

Esempio di integrazione in `src/main.py`, accanto a `make_post`:

```python
from reel.render_reel import render_reel

def make_reel(o: scraper.Offer) -> Path:
    img = Image.open(io.BytesIO(scraper.download(o.photo_url)))
    return render_reel(img, o.short_title, o.price, o.old_price, o.discount, o.historic_low,
                       POSTS / f"{o.post_id}_reel.mp4", cover_path=POSTS / f"{o.post_id}_reel.jpg")
```

## Tempi e animazioni

Tutti i tempi stanno nel dizionario `CUES` in `render_reel.py`. Ogni voce è `(inizio, durata in cui resta gonfio)`.

**Scena 1, "schermo-prezzo" (0 – 3,27 s)**
- Fondo rosso `#E12D39` con una raggiera arancio-oro che gira a 25°/s.
- **0,00 s:** esplodono insieme la card bianca del prodotto (in alto, inclinata di −4°), la stella gialla, la scritta "SOLO" e il prezzo nuovo gigante (rosso con bordo bianco, centrato in basso).
  - Effetti: flash bianco di 0,1 s, scossa dello schermo di 0,35 s, "pop" forte e "ding" da cassa.
- **0,00 s:** insieme al prezzo nuovo compare anche "invece di <prezzo vecchio>", già barrato.

**Transizione (3,27 – 3,59 s)**
- Lo schermo-prezzo si rimpicciolisce fino all'85% e svanisce dentro la card del post.

**Scena 2, grafica del post (3,27 s – fine)**
- Fondo crema `#F7F4EC` con una raggiera dorata che gira a 12°/s.
- Intestazione: logo e "DR.SCOUNT – le offerte migliori, ogni giorno".
- **3,27 s:** la card del prodotto, il nastro "MINIMO STORICO" e il titolo esplodono insieme. La stella è già al suo posto, con il prezzo nuovo (verde) al centro e il prezzo vecchio barrato sopra.
- **4,35 s:** il badge "−XX%" si gonfia.
- **5,75 s:** compare la pillola "OFFERTA NEL LINK IN BIO ↑", che poi pulsa.
- **~8,45 s:** fine, sull'accordo finale del jingle.

**Come "si gonfia" un elemento (`punch`)**
- Esplode in 0,14 s fino al picco, che va da ×1,2 a ×1,45 secondo l'elemento.
- Resta gonfio, fermo, per la durata indicata.
- Si sgonfia con un rimbalzo in 0,35 s, poi "respira" leggermente.

**Audio**
- Jingle synth anni '80 a 128 BPM, con il giro Do–Sol–Lam–Fa.
- "Pop" a ogni elemento, "ding" sul prezzo e sulla barra.
- Saturazione morbida, livello circa −14,5 LUFS.

**Zone sicure Instagram**
- I contenuti stanno tra y = 210 e y = 1640 circa.
- La parte bassa resta libera per la caption e i pulsanti.

## Pubblicazione su Instagram (Graph API)

I reel si pubblicano come i post, ma con `media_type=REELS` e `video_url`. Prima di pubblicare bisogna aspettare che Instagram finisca di elaborare il video:

1. `POST /{IG_USER_ID}/media` con `media_type=REELS`, `video_url=<URL pubblico dell'mp4>`, `caption=...` e, se si vuole, `share_to_feed=true`.
2. `GET /{creation_id}?fields=status_code` ogni 5–10 secondi, finché non risponde `FINISHED`. Se risponde `ERROR`, va segnalato.
3. `POST /{IG_USER_ID}/media_publish` con `creation_id`.

Il file deve essere scaricabile da un URL pubblico, come succede oggi con le immagini su raw.githubusercontent.com. Ogni reel pesa circa 3,5–4 MB.
