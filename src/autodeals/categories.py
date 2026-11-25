"""Categorie di ricerca. Ogni categoria ha un indice Amazon (SearchIndex del marketplace italiano)
e un elenco di parole chiave a rotazione: l'API cerca per parola chiave, non "tutte le offerte"."""

# parole che indicano un accessorio/ricambio e non il prodotto vero
ACCESSORI = ["supporto", "staffa", "mensola", "mobile tv", "porta tv", "carrello", "telecomando", "cavo", "antenna",
             "decoder", "stick", "copertura", "filtro", "tubo", "guarnizione", "ricambio", "ricambi", "kit",
             "adattatore", "cestello", "piedini", "pellicola", "protezione", "pulitore", "detersivo", "anticalcare",
             "manopola", "staffe", "rack", "ripiano", "base", "spugna", "tappetino", "custodia", "cover",
             "pastiglie", "sacchetti", "lampada", "pulizia", "scatola", "contenitore", "stand", "cuscino"]

CATEGORIES = {
    "elettrodomestici": {
        "label": "Grandi elettrodomestici", "index": "Appliances",
        "keywords": ["lavatrice", "frigorifero", "lavastoviglie", "forno", "asciugatrice", "congelatore",
                     "piano cottura", "condizionatore", "cappa", "lavasciuga", "smart tv|Electronics",
                     "televisore 4k|Electronics", "tv oled|Electronics", "tv led|Electronics"],
        # il titolo deve nominare uno di questi (parole intere) e non essere un accessorio
        "must": ["lavatrice", "lavatrici", "lavasciuga", "asciugatrice", "asciugatrici", "frigorifero", "frigo",
                 "congelatore", "lavastoviglie", "lavastoviglie", "forno", "piano cottura", "cappa",
                 "condizionatore", "climatizzatore", "tv", "televisore", "smart tv", "oled", "qled",
                 "cucina a gas", "frigocongelatore", "combinato", "side by side"],
        "not": ACCESSORI,
        "prezzo_min": 90,
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
        # "Casa" cerca su tutto Amazon: servono parole del titolo che confermino il prodotto
        "must": ["detersivo", "pentola", "pentole", "padella", "aspirapolvere", "lenzuola", "lenzuolo", "piumone",
                 "organizer", "termica", "friggitrice", "frullatore", "ferro da stiro", "materasso", "set", "caffè",
                 "bollitore", "tostapane", "scopa", "robot", "asciugamani", "coperta", "tappeto", "cuscino"],
        "not": ["tv", "smartphone", "cuffie"],
    },
    "cura_persona": {
        "label": "Bellezza e cura persona", "index": "Beauty",
        "keywords": ["shampoo", "crema viso", "profumo", "rasoio", "spazzolino elettrico", "deodorante",
                     "siero viso", "bagnoschiuma", "asciugacapelli"],
    },
    "elettronica": {
        "label": "Elettronica", "index": "Electronics",
        "keywords": ["cuffie", "caricatore", "smartwatch", "tablet", "robot aspirapolvere", "telecamera",
                     "altoparlante", "power bank", "soundbar"],
        "not": ["custodia", "cover", "pellicola", "vetro temperato", "televisore", "tv oled", "smart tv"],
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
