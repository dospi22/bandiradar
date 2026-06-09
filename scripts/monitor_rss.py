"""
BandiRadar — monitor_rss.py
Monitora le fonti nazionali e regionali ER tramite RSS feed e check HTTP.
Individua nuovi contenuti potenzialmente rilevanti da verificare manualmente.

USO:
    python scripts/monitor_rss.py
    python scripts/monitor_rss.py --days 14   # cerca novità degli ultimi 14 giorni
    python scripts/monitor_rss.py --fonte invitalia

REQUISITI:
    pip install feedparser requests beautifulsoup4
"""

import argparse
import sys
import re
from datetime import date, datetime, timedelta

try:
    import feedparser
except ImportError:
    print("❌ feedparser non installato. Esegui: pip install feedparser requests")
    sys.exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ requests / beautifulsoup4 non installati. Esegui: pip install requests beautifulsoup4")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# FONTI CONFIGURATE (da documento BandiRadar v3.0)
# ─────────────────────────────────────────────────────────────

FONTI_RSS = [
    {
        "nome": "Invitalia — Incentivi imprese",
        "livello": "Nazionale",
        "url_rss": "https://www.invitalia.it/rss/news.xml",
        "url_web": "https://www.invitalia.it",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "MIMIT — Comunicati stampa",
        "livello": "Nazionale",
        "url_rss": "https://www.mimit.gov.it/it/rss/comunicati",
        "url_web": "https://www.mimit.gov.it/it/incentivi",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "Incentivi.gov — Catalogo nazionale",
        "livello": "Nazionale",
        "url_rss": "",  # nessun RSS disponibile — check manuale
        "url_web": "https://www.incentivi.gov.it/it/catalogo",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "nome": "Bandi.gov.it — Portale nazionale",
        "livello": "Nazionale",
        "url_rss": "https://bandi.gov.it/rss/bandi.xml",
        "url_web": "https://bandi.gov.it",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "Euknow — Bandi UE e nazionali",
        "livello": "Nazionale/UE",
        "url_rss": "https://euknow.it/feed/",
        "url_web": "https://euknow.it",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "Regione Emilia-Romagna — Finanziamenti imprese",
        "livello": "Regionale ER",
        "url_rss": "https://imprese.regione.emilia-romagna.it/rss",
        "url_web": "https://imprese.regione.emilia-romagna.it/bandi",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "Regione ER — Sociale e Terzo Settore",
        "livello": "Regionale ER",
        "url_rss": "",
        "url_web": "https://sociale.regione.emilia-romagna.it/bandi",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "nome": "ART-ER — Bandi e opportunità",
        "livello": "Regionale ER",
        "url_rss": "https://www.art-er.it/feed/",
        "url_web": "https://www.art-er.it/bandi/",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "nome": "INFOBANDI CSVNET — Terzo Settore",
        "livello": "Nazionale",
        "url_rss": "https://infobandi.csvnet.it/feed",
        "url_web": "https://infobandi.csvnet.it",
        "metodo": "RSS",
        "frequenza": "bisettimanale",
    },
]

# Parole chiave per filtrare i contenuti rilevanti
KEYWORDS_POSITIVI = [
    "bando", "agevolazione", "incentivo", "contributo", "finanziamento",
    "credito d'imposta", "voucher", "fondo perduto", "sportello", "aperto",
    "pmi", "impresa", "startup", "innovazione", "digitale", "sostenibilità",
    "internazionalizzazione", "ricerca", "sviluppo", "emilia-romagna",
    "mimit", "invitalia", "simest", "regione er", "por-fesr", "fse",
    "horizon", "eic", "life", "interreg", "pnrr", "fesr"
]

KEYWORDS_NEGATIVI = [
    "webinar", "evento", "conferenza", "formazione", "seminario",
    "consultazione pubblica", "bozza", "in arrivo", "annuncio generico",
    "comunicato stampa", "nota stampa"
]


# ─────────────────────────────────────────────────────────────
# FETCH RSS
# ─────────────────────────────────────────────────────────────

def fetch_rss(fonte: dict, days_back: int) -> list:
    """Scarica e filtra un feed RSS."""
    if not fonte.get("url_rss"):
        return []

    cutoff = datetime.now() - timedelta(days=days_back)

    try:
        feed = feedparser.parse(fonte["url_rss"])
    except Exception as e:
        print(f"  ⚠️  Errore RSS {fonte['nome']}: {e}")
        return []

    if feed.bozo and not feed.entries:
        print(f"  ⚠️  Feed non valido: {fonte['url_rss']}")
        return []

    risultati = []
    for entry in feed.entries:
        # Controlla data
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6])

        if pub_date and pub_date < cutoff:
            continue  # troppo vecchio

        # Analisi rilevanza
        testo = (
            getattr(entry, "title", "") + " " +
            getattr(entry, "summary", "") + " " +
            getattr(entry, "description", "")
        ).lower()

        punteggio_pos = sum(1 for kw in KEYWORDS_POSITIVI  if kw in testo)
        punteggio_neg = sum(1 for kw in KEYWORDS_NEGATIVI  if kw in testo)

        if punteggio_pos < 1 or punteggio_neg > punteggio_pos:
            continue  # probabilmente non è un vero bando

        risultati.append({
            "fonte":    fonte["nome"],
            "livello":  fonte["livello"],
            "titolo":   getattr(entry, "title", "—"),
            "data":     pub_date.strftime("%d/%m/%Y") if pub_date else "—",
            "link":     getattr(entry, "link", fonte["url_web"]),
            "punteggio": punteggio_pos,
            "metodo":   "RSS",
        })

    return risultati


# ─────────────────────────────────────────────────────────────
# CHECK MANUALE (fonti senza RSS)
# ─────────────────────────────────────────────────────────────

def check_manuale(fonte: dict) -> list:
    """Per le fonti senza RSS, stampa solo il promemoria di check manuale."""
    return [{
        "fonte":    fonte["nome"],
        "livello":  fonte["livello"],
        "titolo":   f"⚠️  CHECK MANUALE RICHIESTO — Visita: {fonte['url_web']}",
        "data":     "—",
        "link":     fonte["url_web"],
        "punteggio": 0,
        "metodo":   "Manuale",
    }]


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Monitor RSS Fonti BandiRadar")
    parser.add_argument("--days", type=int, default=7,
                        help="Giorni indietro da monitorare (default: 7)")
    parser.add_argument("--fonte", default="",
                        help="Filtra per nome fonte (parziale, case-insensitive)")
    parser.add_argument("--livello", default="",
                        choices=["", "Nazionale", "Regionale ER", "Nazionale/UE"],
                        help="Filtra per livello")
    args = parser.parse_args()

    print("=" * 65)
    print("📡 BandiRadar — Monitor RSS Fonti Nazionali e Regionali ER")
    print(f"📅 Data: {date.today().isoformat()}  |  Periodo: ultimi {args.days} giorni")
    print("=" * 65)

    fonti = FONTI_RSS
    if args.fonte:
        fonti = [f for f in fonti if args.fonte.lower() in f["nome"].lower()]
    if args.livello:
        fonti = [f for f in fonti if f["livello"] == args.livello]

    if not fonti:
        print("❌ Nessuna fonte trovata con i filtri specificati.")
        return

    tutti_risultati = []
    manuali         = []

    for fonte in fonti:
        print(f"\n🔍 {fonte['nome']} [{fonte['livello']}]")

        if fonte["metodo"] == "RSS" or fonte.get("url_rss"):
            risultati = fetch_rss(fonte, args.days)
            if risultati:
                print(f"   ✅ {len(risultati)} elementi potenzialmente rilevanti")
                tutti_risultati.extend(risultati)
            else:
                print(f"   ℹ️  Nessuna novità negli ultimi {args.days} giorni")
        else:
            print(f"   📋 Nessun RSS — richiede check manuale")
            manuali.extend(check_manuale(fonte))

    # Ordina per punteggio rilevanza
    tutti_risultati.sort(key=lambda x: x["punteggio"], reverse=True)

    # Riepilogo
    print("\n" + "=" * 65)
    print(f"📊 RIEPILOGO: {len(tutti_risultati)} risultati da verificare + {len(manuali)} check manuali")
    print("=" * 65)

    if tutti_risultati:
        print("\n🔎 BANDI POTENZIALI DA VERIFICARE (ordine per rilevanza):\n")
        for i, r in enumerate(tutti_risultati, 1):
            print(f"[{i:2}] {r['titolo'][:70]}")
            print(f"     📅 {r['data']}  |  🏛️ {r['livello']}  |  📡 {r['fonte']}")
            print(f"     🔗 {r['link']}")
            print()

    if manuali:
        print("\n📋 CHECK MANUALI DA ESEGUIRE:\n")
        for m in manuali:
            print(f"  → {m['fonte']}")
            print(f"     {m['link']}\n")

    print("─" * 65)
    print("✅ PROSSIMI PASSI:")
    print("   1. Per ogni risultato: apri il link e verifica che sia un bando reale")
    print("   2. Se è un bando reale → aggiungi una riga in data/bandi.csv")
    print("   3. Se è un falso positivo → annota per escluderlo dalle prossime scansioni")
    print("   4. Per i check manuali → visita il sito e scansiona i bandi recenti")
    print("─" * 65)


if __name__ == "__main__":
    main()
