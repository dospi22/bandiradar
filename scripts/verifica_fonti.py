#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — verifica_fonti.py
══════════════════════════════
Health-check di TUTTE le fonti monitorate (scripts/fonti.py):
  - feed RSS:  raggiungibile? parsabile? quanto è recente l'ultima voce?
  - pagine:    raggiungibili? contenuto non vuoto?

Scrive il risultato in data/fonti_status.json — la dashboard lo legge per
mostrare l'avviso "fonte cieca" (un feed morto = novità che non vedi).

Stati possibili per fonte:
  OK        funziona e ha contenuti recenti
  STANTIO   feed raggiungibile ma ultima voce > 90 giorni (sospetto feed morto)
  ERRORE    irraggiungibile / non parsabile / vuoto
  BLOCCATO  HTTP 403 da protezione anti-bot (WAF): fonte probabilmente attiva, check dal browser
  MANUALE   fonte a check manuale (non testabile automaticamente)

USO:
    python scripts/verifica_fonti.py
    (in GitHub Actions: workflow monitor-fonti.yml, ogni lunedì)

REQUISITI:
    pip install feedparser requests

Exit code: 0 sempre. Il numero di fonti in errore è nel JSON e nello stdout.
"""

import json
import os
import sys
from datetime import datetime, timedelta

try:
    import requests
    import feedparser
except ImportError:
    print("❌ requests / feedparser non installati. Esegui: pip install requests feedparser")
    sys.exit(1)

from fonti import FONTI_RSS, FONTI_PAGINE

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, 'data', 'fonti_status.json')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.5",
}
TIMEOUT = 30
GIORNI_STANTIO = 90


def check_rss(fonte: dict) -> dict:
    """Verifica un feed RSS. Ritorna record di stato."""
    rec = {
        "id": fonte["id"], "nome": fonte["nome"], "livello": fonte["livello"],
        "tipo": "RSS", "url": fonte["url_rss"] or fonte["url_web"],
    }
    if not fonte.get("url_rss"):
        rec.update(status="MANUALE", dettaglio="Fonte a check manuale (nessun RSS)")
        return rec
    try:
        resp = requests.get(fonte["url_rss"], headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 403:
            rec.update(status="BLOCCATO",
                       dettaglio="HTTP 403 — protezione anti-bot (WAF): la fonte è quasi certamente attiva, verificare dal browser")
            return rec
        if resp.status_code != 200:
            rec.update(status="ERRORE", dettaglio=f"HTTP {resp.status_code}")
            return rec
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            rec.update(status="ERRORE", dettaglio="Feed vuoto o non parsabile (0 voci)")
            return rec
        # data della voce più recente
        ultima = None
        for e in feed.entries:
            for attr in ("published_parsed", "updated_parsed"):
                t = getattr(e, attr, None)
                if t:
                    d = datetime(*t[:6])
                    if ultima is None or d > ultima:
                        ultima = d
        rec["voci"] = len(feed.entries)
        if ultima:
            rec["ultima_voce"] = ultima.strftime("%Y-%m-%d")
            if datetime.now() - ultima > timedelta(days=GIORNI_STANTIO):
                rec.update(status="STANTIO",
                           dettaglio=f"Ultima voce del {ultima.strftime('%d/%m/%Y')}: feed sospetto")
                return rec
        rec.update(status="OK", dettaglio=f"{len(feed.entries)} voci")
        return rec
    except Exception as e:
        rec.update(status="ERRORE", dettaglio=str(e)[:150])
        return rec


def check_pagina(fonte: dict) -> dict:
    """Verifica che una pagina monitorata a diff sia raggiungibile."""
    rec = {
        "id": fonte["id"], "nome": fonte["nome"], "livello": fonte["livello"],
        "tipo": "Diff pagina", "url": fonte["url_web"],
    }
    try:
        resp = requests.get(fonte["url_web"], headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 403:
            rec.update(status="BLOCCATO",
                       dettaglio="HTTP 403 — protezione anti-bot (WAF): la pagina è quasi certamente attiva, verificare dal browser")
        elif resp.status_code != 200:
            rec.update(status="ERRORE", dettaglio=f"HTTP {resp.status_code}")
        elif len(resp.text) < 500:
            rec.update(status="ERRORE", dettaglio=f"Contenuto sospetto ({len(resp.text)} byte)")
        else:
            rec.update(status="OK", dettaglio=f"{len(resp.text)//1024} KB")
    except Exception as e:
        rec.update(status="ERRORE", dettaglio=str(e)[:150])
    return rec


def main():
    print("=" * 65)
    print("🩺 BandiRadar — Health-check fonti")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    risultati = []
    for f in FONTI_RSS:
        rec = check_rss(f)
        risultati.append(rec)
        icona = {"OK": "✅", "STANTIO": "🟡", "ERRORE": "❌", "MANUALE": "📋", "BLOCCATO": "🛡️"}.get(rec["status"], "❓")
        print(f"{icona} [{rec['status']:7}] {rec['nome']} — {rec['dettaglio']}")
    for f in FONTI_PAGINE:
        rec = check_pagina(f)
        risultati.append(rec)
        icona = {"OK": "✅", "ERRORE": "❌", "BLOCCATO": "🛡️"}.get(rec["status"], "❓")
        print(f"{icona} [{rec['status']:7}] {rec['nome']} — {rec['dettaglio']}")

    n_ok       = sum(1 for r in risultati if r["status"] == "OK")
    n_errore   = sum(1 for r in risultati if r["status"] == "ERRORE")
    n_stantio  = sum(1 for r in risultati if r["status"] == "STANTIO")
    n_manuale  = sum(1 for r in risultati if r["status"] == "MANUALE")
    n_bloccato = sum(1 for r in risultati if r["status"] == "BLOCCATO")

    out = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "data": datetime.now().strftime("%Y-%m-%d"),
        "ok": n_ok, "errore": n_errore, "stantio": n_stantio, "manuale": n_manuale,
        "bloccato": n_bloccato,
        "totale": len(risultati),
        "fonti": risultati,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 65)
    print(f"📊 {n_ok} OK | {n_stantio} stantii | {n_errore} in errore | {n_bloccato} bloccate (WAF) | {n_manuale} manuali")
    print(f"💾 Salvato: data/fonti_status.json")
    print("=" * 65)
    if n_errore or n_stantio:
        print("\n⚠️  ATTENZIONE: fonti cieche = bandi che potresti non vedere.")
        print("   Verifica gli URL in scripts/fonti.py o cerca feed alternativi.")


if __name__ == "__main__":
    main()
