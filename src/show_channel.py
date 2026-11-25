"""Stampa il testo (con link ed emoji) degli ultimi post del canale: serve a copiare lo stile."""
import requests
from bs4 import BeautifulSoup

html = requests.get("https://t.me/s/drscount", timeout=30).text
for msg in BeautifulSoup(html, "html.parser").select(".tgme_widget_message")[-4:]:
    el = msg.select_one(".tgme_widget_message_text")
    if not el:
        continue
    for br in el.find_all("br"):
        br.replace_with("\n")
    for a in el.find_all("a"):
        a.append(f" <<{a.get('href')}>>")
    print(el.get_text()); print("-" * 40)
    print("BOTTONI:", [(b.get_text(), b.get("href")) for b in msg.select(".tgme_widget_message_inline_button")])
    print("=" * 40)
