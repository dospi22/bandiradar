"""
BandiRadar — monitor_eu.py
Monitora il portale EU Funding & Tenders via API REST ufficiale.
Restituisce una lista di opportunità potenzialmente rilevanti per PMI italiane.

USO:
    python scripts/monitor_eu.py
    python scripts/monitor_eu.py --keywords "PMI digitale sostenibilità" --max 50

OUTPUT:
    Stampa i bandi trovati in formato leggibile.
    Opzionalmente salva in /tmp/eu_bandi_trovati.csv
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError


# ─────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ─────────────────────────────────────────────────────────────

EU_API_BASE = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"

# Parole chiave rilevanti per il portafoglio clienti (modifica secondo necessità)
DEFAULT_KEYWORDS = [
    "SME", "innovation", "digital", "sustainability", "Emilia-Romagna",
    "Italy", "manufacturing", "green transition", "startup", "research"
]

# Programmi di interesse
PROGRAMS_OF_INTEREST = [
    "HORIZON", "EIC", "LIFE", "COSME", "INTERREG",
    "ERDF", "ESF", "PNRR", "InvestEU"
]

# Filtri per paesi ammissibili
COUNTRIES = ["IT"]  # Italia


# ─────────────────────────────────────────────────────────────
# CHIAMATA API
# ─────────────────────────────────────────────────────────────

def call_eu_api(query: str, page_size: int = 30, page_num: int = 1) -> dict:
    """Chiama l'API EU Funding & Tenders."""
    params = {
        "query":    query,
        "pageSize": page_size,
        "pageNum":  page_num,
        "languages": "it,en",
        "facets":   json.dumps({
            "type": ["1"],            # 1 = Call/Bando
            "status": ["open", "forthcoming"],
        }),
    }
    url = f"{EU_API_BASE}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())
    except URLError as e:
        print(f"⚠️  Errore connessione API EU: {e}", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print("⚠️  Risposta API non valida (JSON malformato)", file=sys.stderr)
        return {}


# ─────────────────────────────────────────────────────────────
# PARSING RISULTATI
# ─────────────────────────────────────────────────────────────

def parse_opportunity(item: dict) -> dict:
    """Estrae i campi rilevanti da un item dell'API."""
    metadata   = item.get("metadata", {})
    identifier = item.get("identifier", "")

    return {
        "id_eu":      identifier,
        "titolo":     item.get("title", "—"),
        "programma":  metadata.get("programmeName", ["—"])[0] if metadata.get("programmeName") else "—",
        "tipo":       metadata.get("type", ["—"])[0] if metadata.get("type") else "—",
        "stato":      metadata.get("status", "—"),
        "apertura":   metadata.get("startDate", "—"),
        "scadenza":   metadata.get("deadlineDate", "—"),
        "budget":     metadata.get("budgetMax", "—"),
        "link":       f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{identifier}",
        "descrizione": item.get("description", "")[:200] + "..." if item.get("description") else "—",
    }


def is_relevant(opp: dict) -> bool:
    """Filtra le opportunità più rilevanti per il contesto italiano/ER."""
    titolo = opp["titolo"].lower()
    prog   = opp["programma"].upper()

    # Includi se il programma è di interesse
    for p in PROGRAMS_OF_INTEREST:
        if p in prog:
            return True

    # Includi se il titolo contiene parole chiave rilevanti
    keywords_it = ["pmi", "sme", "innovaz", "digital", "green", "sostenibi",
                   "italian", "italia", "emilia", "startup", "ricerca", "r&s"]
    for kw in keywords_it:
        if kw in titolo:
            return True

    return False


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Monitor EU Funding Portal")
    parser.add_argument("--keywords", default=" ".join(DEFAULT_KEYWORDS[:5]),
                        help="Parole chiave per la ricerca")
    parser.add_argument("--max", type=int, default=50,
                        help="Numero massimo di risultati da scaricare")
    parser.add_argument("--output", default="",
                        help="Percorso CSV output (opzionale)")
    args = parser.parse_args()

    print("=" * 60)
    print("📡 BandiRadar — Monitor EU Funding Portal")
    print(f"🔍 Query: {args.keywords}")
    print(f"📅 Data: {date.today().isoformat()}")
    print("=" * 60)

    # Chiamata API (max 2 pagine per non sovraccaricare)
    all_items = []
    for page in range(1, 3):
        print(f"\n📥 Pagina {page}...")
        result  = call_eu_api(args.keywords, page_size=25, page_num=page)
        items   = result.get("results", [])
        if not items:
            break
        all_items.extend(items)
        if len(all_items) >= args.max:
            break

    if not all_items:
        print("\n⚠️  Nessun risultato dall'API. Verifica la connessione.")
        print("    URL API: " + EU_API_BASE)
        return

    # Parsing e filtro
    opportunities = [parse_opportunity(i) for i in all_items]
    relevant      = [o for o in opportunities if is_relevant(o)]

    print(f"\n✅ {len(all_items)} risultati totali → {len(relevant)} potenzialmente rilevanti\n")

    if not relevant:
        print("ℹ️  Nessuna opportunità rilevante trovata con i filtri attuali.")
        print("   Prova a modificare le parole chiave.")
        return

    # Stampa risultati
    print("─" * 60)
    for i, opp in enumerate(relevant, 1):
        print(f"\n[{i}] {opp['titolo']}")
        print(f"    Programma: {opp['programma']}  |  Stato: {opp['stato']}")
        print(f"    Apertura: {opp['apertura']}  →  Scadenza: {opp['scadenza']}")
        print(f"    Budget max: {opp['budget']}")
        print(f"    Link: {opp['link']}")
    print("\n" + "─" * 60)

    # Salva CSV se richiesto
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=relevant[0].keys())
            writer.writeheader()
            writer.writerows(relevant)
        print(f"\n💾 Salvato in: {args.output}")

    print(f"\n✅ ISTRUZIONE: verifica ciascuno dei {len(relevant)} bandi sopra.")
    print("   Per ogni bando reale, inserisci una nuova riga nel Google Sheet.")
    print("   Per i falsi positivi, annotali nel foglio 'Scartati'.")


if __name__ == "__main__":
    main()
