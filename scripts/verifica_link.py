"""
verifica_link.py
================
Legge bandi.csv e testa ogni link ufficiale dei bandi attivi.
Produce un report con: OK / REDIRECT / 404 / ERRORE per ogni URL.

Uso:
    pip install requests
    python scripts/verifica_link.py

    # Solo bandi attivi (default):
    python scripts/verifica_link.py

    # Tutti i bandi (inclusi Sospeso/In arrivo):
    python scripts/verifica_link.py --tutti

    # Salva report su file:
    python scripts/verifica_link.py --output report_link.txt
"""

import csv
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
    from requests.exceptions import RequestException, Timeout, ConnectionError as ConnErr
except ImportError:
    print("ERRORE: libreria 'requests' non installata.")
    print("Esegui: pip install requests")
    sys.exit(1)

BASE_DIR        = Path(__file__).parent.parent
CSV_PATH        = BASE_DIR / "data" / "bandi.csv"
LINK_STATUS_PATH = BASE_DIR / "data" / "link_status.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

TIMEOUT = 12       # secondi per richiesta
PAUSA   = 0.8      # pausa tra richieste (educata verso i server)

# Parole che indicano pagina non trovata anche con status 200
KEYWORD_404 = [
    "pagina non trovata", "page not found", "404", "non è possibile trovare",
    "this page does not exist", "errore 404", "risorsa non trovata",
    "la pagina richiesta non esiste", "contenuto non trovato",
]

# Parole che confermano che la pagina è quella giusta
KEYWORD_OK = [
    "bando", "agevolazione", "contributo", "finanziamento", "voucher",
    "scadenza", "domanda", "candidatura", "sportello", "incentivo",
    "2025", "2026", "2027", "deadline", "apply", "eligible",
]


def controlla_link(url: str) -> dict:
    """
    Testa un URL e restituisce un dict con:
        status   : "OK" | "REDIRECT" | "404" | "ERRORE" | "VUOTO"
        codice   : HTTP status code (int) o None
        finale   : URL finale dopo redirect
        nota     : spiegazione breve
    """
    if not url or not url.startswith("http"):
        return {"status": "ERRORE", "codice": None, "finale": url, "nota": "URL non valido o mancante"}

    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        codice = resp.status_code
        finale = resp.url
        testo  = resp.text[:5000].lower()

        # Redirect significativo (dominio cambiato o path molto diverso)
        redirect = (finale.rstrip("/") != url.rstrip("/"))
        dominio_orig  = url.split("/")[2] if len(url.split("/")) > 2 else ""
        dominio_final = finale.split("/")[2] if len(finale.split("/")) > 2 else ""
        redirect_esterno = (dominio_orig != dominio_final)

        if codice == 404:
            return {"status": "404", "codice": 404, "finale": finale, "nota": "Pagina non trovata (HTTP 404)"}

        if codice >= 400:
            return {"status": "ERRORE", "codice": codice, "finale": finale, "nota": f"HTTP {codice}"}

        # Controlla contenuto anche con 200
        for kw in KEYWORD_404:
            if kw in testo:
                return {"status": "404", "codice": codice, "finale": finale, "nota": f"Pagina 404 mascherata (trovato: '{kw}')"}

        # Pagina quasi vuota (JS-heavy, non caricata)
        if len(resp.text.strip()) < 400:
            return {"status": "VUOTO", "codice": codice, "finale": finale, "nota": "Pagina vuota/JS-heavy — verifica manualmente"}

        # Segnali positivi
        segnali = sum(1 for kw in KEYWORD_OK if kw in testo)

        if redirect_esterno:
            return {
                "status": "REDIRECT",
                "codice": codice,
                "finale": finale,
                "nota": f"Redirect verso dominio diverso: {dominio_final} (segnali bando: {segnali})",
            }

        if redirect and segnali < 2:
            return {
                "status": "REDIRECT",
                "codice": codice,
                "finale": finale,
                "nota": f"Redirect interno, pochi segnali bando ({segnali}/7)",
            }

        return {
            "status": "OK",
            "codice": codice,
            "finale": finale,
            "nota": f"Segnali bando rilevati: {segnali}/7",
        }

    except Timeout:
        return {"status": "ERRORE", "codice": None, "finale": url, "nota": f"Timeout dopo {TIMEOUT}s"}
    except ConnErr as e:
        return {"status": "ERRORE", "codice": None, "finale": url, "nota": f"Connessione fallita: {e}"}
    except RequestException as e:
        return {"status": "ERRORE", "codice": None, "finale": url, "nota": f"Errore richiesta: {e}"}


def leggi_bandi(solo_attivi: bool = True) -> list:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if solo_attivi:
        return [r for r in rows if r.get("Stato") in ("Aperto", "In apertura")]
    return rows


def salva_link_status(risultati: dict, now_iso: str) -> None:
    """
    Salva data/link_status.json — letto dalla dashboard per mostrare
    lo stato di ogni link senza che l'utente debba cliccarci.

    Struttura:
    {
      "generatedAt": "2026-05-26T08:00:00Z",
      "bandi": {
        "EU-2026-001": { "status": "OK",   "codice": 200, "nota": "...", "checkedAt": "..." },
        "IT-2026-002": { "status": "404",  "codice": 404, "nota": "...", "checkedAt": "..." },
        ...
      }
    }
    """
    # Carica lo stato precedente (per mantenere i bandi non controllati in questa run)
    stato_precedente = {}
    if LINK_STATUS_PATH.exists():
        try:
            stato_precedente = json.loads(LINK_STATUS_PATH.read_text(encoding="utf-8")).get("bandi", {})
        except Exception:
            pass

    # Aggiorna con i risultati di questa run
    nuovi = {}
    for categoria, items in risultati.items():
        for r in items:
            nuovi[r["id"]] = {
                "status":    r["status"],
                "codice":    r.get("codice"),
                "nota":      r.get("nota", ""),
                "checkedAt": now_iso,
            }

    stato_finale = {**stato_precedente, **nuovi}

    payload = {
        "generatedAt": now_iso,
        "bandi": stato_finale,
    }

    LINK_STATUS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ link_status.json aggiornato ({len(stato_finale)} bandi totali)")


def main():
    parser = argparse.ArgumentParser(description="Verifica link bandi BandiRadar")
    parser.add_argument("--tutti",    action="store_true", help="Controlla tutti i bandi (non solo attivi)")
    parser.add_argument("--output",   type=str, default=None, help="Salva report testuale su file")
    parser.add_argument("--no-json",  action="store_true", help="Non aggiornare link_status.json")
    args = parser.parse_args()

    bandi    = leggi_bandi(solo_attivi=not args.tutti)
    now      = datetime.now().strftime("%Y-%m-%d %H:%M")
    now_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    linee = []
    linee.append("=" * 65)
    linee.append(f"  BandiRadar — Verifica link ufficiali  [{now}]")
    linee.append(f"  Bandi controllati: {len(bandi)} {'(solo attivi)' if not args.tutti else '(tutti)'}")
    linee.append("=" * 65)

    risultati = {"OK": [], "REDIRECT": [], "404": [], "ERRORE": [], "VUOTO": []}

    for i, b in enumerate(bandi, 1):
        bid   = b.get("ID", "?")
        nome  = b.get("Nome bando", "?")[:55]
        link  = b.get("Link ufficiale", "").strip()
        stato = b.get("Stato", "")

        print(f"  [{i:02d}/{len(bandi)}] {bid}...", end=" ", flush=True)
        res = controlla_link(link)
        print(res["status"])

        riga = {
            "id": bid,
            "nome": nome,
            "stato_bando": stato,
            "link": link,
            **res,
        }
        risultati[res["status"]].append(riga)
        time.sleep(PAUSA)

    # Salva JSON leggibile dalla dashboard
    if not args.no_json:
        salva_link_status(risultati, now_iso)

    # Stampa report testuale
    linee.append("")
    for categoria, icona in [("404", "ROTTO"), ("ERRORE", "ERRORE"), ("REDIRECT", "REDIRECT"), ("VUOTO", "DA VERIF."), ("OK", "OK")]:
        items = risultati[categoria]
        if not items:
            continue
        linee.append(f"\n{'─'*65}")
        linee.append(f"  {icona} ({len(items)})")
        linee.append(f"{'─'*65}")
        for r in items:
            linee.append(f"  {r['id']:15} {r['nome']}")
            linee.append(f"    Stato bando : {r['stato_bando']}")
            linee.append(f"    URL         : {r['link']}")
            if r["finale"] != r["link"]:
                linee.append(f"    URL finale  : {r['finale']}")
            linee.append(f"    Nota        : {r['nota']}")

    # Riepilogo
    linee.append(f"\n{'='*65}")
    linee.append("  RIEPILOGO")
    linee.append(f"{'='*65}")
    linee.append(f"  OK           : {len(risultati['OK'])}")
    linee.append(f"  Redirect     : {len(risultati['REDIRECT'])}")
    linee.append(f"  404/Rotto    : {len(risultati['404'])}")
    linee.append(f"  Errore conn. : {len(risultati['ERRORE'])}")
    linee.append(f"  Da verificare: {len(risultati['VUOTO'])}")
    n_problemi = len(risultati["404"]) + len(risultati["ERRORE"]) + len(risultati["REDIRECT"])
    linee.append(f"\n  Link da correggere: {n_problemi}")
    linee.append("=" * 65)

    output = "\n".join(linee)
    print("\n" + output)

    if args.output:
        out_path = BASE_DIR / args.output
        out_path.write_text(output, encoding="utf-8")
        print(f"\nReport salvato: {out_path}")

    return 0 if n_problemi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
