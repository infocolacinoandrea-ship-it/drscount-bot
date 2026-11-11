# Dr.Scount bot: dal canale Telegram a Instagram

Ogni 15 minuti, dalle 7 alle 23 circa, il bot:

1. legge il canale pubblico **t.me/drscount**;
2. sceglie le offerte migliori tra quelle nuove. Conta lo sconto, il minimo storico, le stelle, le recensioni e un bonus per i prodotti per la casa;
3. crea l'immagine 1080×1350 con il prodotto al centro, il prezzo in grande, il prezzo vecchio barrato, il logo e "OFFERTA NEL LINK IN BIO";
4. ti manda l'anteprima su Telegram con i pulsanti **✅ Pubblica** e **❌ Scarta**;
5. quando premi ✅, al giro successivo (entro circa 15 minuti) pubblica il post su Instagram con la caption e ti manda il link.

Il bot gira gratis su **GitHub Actions**, quindi non serve tenere un computer acceso.

---

## Configurazione (circa 30 minuti, una volta sola)

### 1. Bot Telegram per le approvazioni
1. Su Telegram apri **@BotFather**, scrivi `/newbot` e scegli un nome, per esempio *DrScount Assistant*. Copia il **token**.
2. Apri il tuo nuovo bot e premi **Avvia**: senza questo passaggio il bot non può scriverti.
3. Apri **@userinfobot** e copia il tuo **Id**, un numero. È il tuo `TG_ADMIN_CHAT_ID`.

### 2. Account Instagram professionale
1. Nell'app Instagram vai su Impostazioni → *Tipo di account e strumenti* → **Passa a un account professionale**. Va bene *Creator* o *Azienda*. Non serve una Pagina Facebook.

### 3. App Meta e token Instagram
1. Vai su **developers.facebook.com** → *Le mie app* → **Crea app**.
2. Come caso d'uso scegli **"Gestisci messaggi e contenuti su Instagram"** (Instagram API con accesso Instagram).
3. Nella sezione *Configurazione API con accesso Instagram*, alla voce **Genera token d'accesso**, aggiungi l'account @dottorscout e accedi.
4. Copia il **token** (`IG_ACCESS_TOKEN`) e l'**ID utente Instagram** (`IG_USER_ID`).
   Servono i permessi `instagram_business_basic` e `instagram_business_content_publish`. Per pubblicare sul tuo account non serve la revisione dell'app.

### 4. Repository GitHub
1. Crea un account su **github.com**, se non lo hai già.
2. Crea un repository **pubblico** chiamato `drscount-bot` e carica tutti i file di questa cartella.
   Deve essere pubblico perché Instagram scarica le immagini da lì. I segreti restano privati.
3. Vai su *Settings → Secrets and variables → Actions → New repository secret* e aggiungi:
   | Nome | Valore |
   |---|---|
   | `TG_BOT_TOKEN` | token di BotFather |
   | `TG_ADMIN_CHAT_ID` | il tuo Id Telegram |
   | `IG_USER_ID` | ID utente Instagram |
   | `IG_ACCESS_TOKEN` | token Instagram |
4. Vai su *Actions*, abilita i workflow, apri **Dr.Scount bot** e premi **Run workflow** per fare la prima prova.

---

## Regolazioni

In `src/config.py`:

| Impostazione | Default | Cosa fa |
|---|---|---|
| `MIN_DISCOUNT` | 40 | sconto minimo per proporre un'offerta |
| `MIN_RATING` | 4.0 | stelle minime |
| `MIN_REVIEWS` | 50 | recensioni minime |
| `MAX_PREVIEWS_PER_RUN` | 2 | anteprime massime per giro |
| `MAX_PREVIEWS_PER_DAY` | 8 | anteprime massime al giorno |
| `HOME_KEYWORDS` | … | parole che danno priorità ai prodotti per la casa |

Il **logo** è in `assets/logo.png`. Sostituiscilo con un'immagine quadrata in alta risoluzione.
La **grafica** è in `src/render.py`, la **caption** in `src/caption.py`.

## Cose da sapere
- **Token Instagram**: il token dell'app DrScount Autopost (inizia con `EAA`) non scade. Se un giorno usi un token che inizia con `IG`, dura 60 giorni: il bot lo rinnova da solo ogni settimana.
- **Anteprime vecchie**: se non le approvi entro 36 ore scadono, perché il prezzo potrebbe essere cambiato.
- **Prezzi Amazon**: l'immagine e la caption riportano la data del prezzo e la frase sull'affiliazione. Le regole del Programma Affiliazione Amazon sono severe sui prezzi mostrati fuori dal sito, quindi pubblica solo offerte appena uscite. Il sistema è fatto apposta per questo.
- **Ritardi di GitHub**: a volte i giri programmati partono con qualche minuto di ritardo. È normale.

## Prova in locale (facoltativo)
```bash
pip install -r requirements.txt
python src/main.py --dry-run   # crea le immagini in posts/ senza inviare niente
```
