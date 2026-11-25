"""Categorie di ricerca. Ogni categoria ha un indice Amazon (SearchIndex del marketplace italiano)
e un elenco di parole chiave a rotazione: l'API cerca per parola chiave, non "tutte le offerte"."""

CATEGORIES = {
    "elettrodomestici": {
        "label": "Grandi elettrodomestici", "index": "Appliances",
        "keywords": ["lavatrice", "frigorifero", "lavastoviglie", "forno", "asciugatrice", "congelatore",
                     "piano cottura", "condizionatore", "cappa", "asciugatrice a pompa di calore"],
    },
    "abbigliamento": {
        "label": "Abbigliamento", "index": "Apparel",
        "keywords": ["scarpe", "giacca", "jeans", "felpa", "maglione", "sneakers", "pantaloni", "piumino",
                     "t-shirt", "zaino"],
    },
    "casa": {
        "label": "Casa e cucina", "index": "All",
        "keywords": ["detersivo", "pentole", "aspirapolvere", "lenzuola", "piumone", "organizer",
                     "bottiglia termica", "friggitrice ad aria", "frullatore", "ferro da stiro", "materasso"],
    },
    "cura_persona": {
        "label": "Bellezza e cura persona", "index": "Beauty",
        "keywords": ["shampoo", "crema viso", "profumo", "rasoio", "spazzolino elettrico", "deodorante",
                     "siero viso", "bagnoschiuma", "asciugacapelli"],
    },
    "elettronica": {
        "label": "Elettronica", "index": "Electronics",
        "keywords": ["cuffie", "caricatore", "smartwatch", "tablet", "robot aspirapolvere", "telecamera",
                     "altoparlante", "power bank", "tv", "soundbar"],
    },
    "informatica": {
        "label": "Informatica", "index": "Computers",
        "keywords": ["ssd", "monitor", "mouse", "tastiera", "router", "stampante", "hard disk"],
    },
    "infanzia": {
        "label": "Prima infanzia", "index": "Baby",
        "keywords": ["pannolini", "passeggino", "seggiolino", "biberon", "salviette", "lettino"],
    },
}

# Quote giornaliere di partenza (modificabili da Telegram)
DEFAULT_QUOTAS = {"elettrodomestici": 2, "abbigliamento": 3, "casa": 6, "cura_persona": 4,
                  "elettronica": 3, "informatica": 2, "infanzia": 2}
