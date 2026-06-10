#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — monitor_pagine.py
══════════════════════════════
Monitora le fonti SENZA feed RSS (elenco in scripts/fonti.py -> FONTI_PAGINE)
con la tecnica del DIFF: scarica la pagina, estrae i link "da bando",
li confronta con lo snapshot precedente e segnala solo le NOVITÀ.

Lo snapshot è salvato in data/pagine_snapshot.json.
Alla prima esecuzione crea la baseline (nessuna novità segnalata).

USO:
    python scripts/monitor_pagine.py                  # tutte le fonti
    python scripts/monitor_pagine.py --fonte cciaa    # solo una fonte
    python scripts/monitor_pagine.py --dry-run        # non aggiorna lo snapshot

REQUISITI:
    pip install requests beautifulsoup4

Exit code: 0 sempre (anche con fonti irraggiungibili: vengono segnalate).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ requests / beautifulsoup4 non installati. Esegui: pip install requests beautifulsoup4")
    sys.exit(1)

from fonti import FONTI_PAGINE, KEYWORDS_POSITIVI, KEYWORDS_NEGATIVI

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, 'data', 'pagine_snapshot.json')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BandiRadar/1.0; monitoraggio bandi PMI)",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.5",
}
TIMEOUT = 30

# Un link è "interessante" se il testo contiene almeno una keyword positiva
RE_POS = re.compile("|".join(re.escape(k) for k in KEYWORDS_POSITIVI), re.IGNORECASE)
RE_NEG = re.compile("|".join(re.escape(k) for k in KEYWORDS_NEGATIVI), re.IGNORECASE)


def estrai_voci(html: str, base_url: str) -> dict:
    """Estrae dalla pagina i link rilevanti. Ritorna {url_assoluto: titolo}."""
    soup = BeautifulSoup(html, "html.parser")
    voci = {}
    for a in soup.find_all("a", href=True):
        titolo = " ".join(a.get_text(" ", strip=True).split())
        href = a["href"].strip()
        if len(titolo) < 15:              # scarta "vai", "leggi tutto", menu
            continue
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        if not RE_POS.search(titolo):
            continue
        if RE_NEG.search(titolo) and not re.search(r"bando|voucher|contribut", titolo, re.I):
            continue
        url = urljoin(base_url, href)
        # tieni il titolo più lungo se lo stesso link appare più volte
        if url not in voci or len(titolo) > len(voci[url]):
            voci[url] = titolo[:200]
    return voci


def carica_snapshot() -> dict:
    if not os.path.exists(SNAPSHOT):
        return {}
    try:
        with open(SNAPSHOT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def salva_snapshot(snap: dict):
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Monitor diff pagine senza RSS")
    ap.add_argument("--fonte", default="", help="Filtra per id/nome fonte (parziale)")
    ap.add_argument("--dry-run", action="store_true", help="Non aggiornare lo snapshot")
    args = ap.parse_args()

    fonti = FONTI_PAGINE
    if args.fonte:
        q = args.fonte.lower()
        fonti = [f for f in fonti if q in f["id"].lower() or q in f["nome"].lower()]
    if not fonti:
        print("❌ Nessuna fonte trovata con il filtro specificato.")
        return

    snap = carica_snapshot()
    novita_totali = []
    errori = []

    print("=" * 65)
    print("📡 BandiRadar — Monitor pagine senza RSS (diff vs snapshot)")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    for fonte in fonti:
        fid = fonte["id"]
        print(f"\n🔍 {fonte['nome']} [{fonte['livello']}]")
        try:
            resp = requests.get(fonte["url_web"], headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            print(f"   ⚠️  Irraggiungibile: {e}")
            errori.append((fonte["nome"], str(e)))
            continue

        voci = estrai_voci(resp.text, fonte["url_web"])
        print(f"   {len(voci)} voci rilevanti sulla pagina")

        prima_volta = fid not in snap
        voci_vecchie = set(snap.get(fid, {}).get("voci", {}).keys())
        nuove = {u: t for u, t in voci.items() if u not in voci_vecchie}

        if prima_volta:
            print("   📋 Prima scansione: creo la baseline (nessuna novità segnalata)")
        elif nuove:
            print(f"   ✅ {len(nuove)} NOVITÀ rispetto alla scansione precedente:")
            for u, t in nuove.items():
                print(f"      • {t}")
                print(f"        🔗 {u}")
                novita_totali.append({"fonte": fonte["nome"], "livello": fonte["livello"],
                                      "titolo": t, "link": u})
        else:
            print("   ℹ️  Nessuna novità")

        if not args.dry_run:
            snap[fid] = {
                "nome": fonte["nome"],
                "url": fonte["url_web"],
                "ultimo_check": datetime.now().astimezone().isoformat(),
                "voci": voci if voci else snap.get(fid, {}).get("voci", {}),
            }

    if not args.dry_run:
        salva_snapshot(snap)
        print(f"\n💾 Snapshot aggiornato: data/pagine_snapshot.json")

    print("\n" + "=" * 65)
    print(f"📊 RIEPILOGO: {len(novita_totali)} novità | {len(errori)} fonti irraggiungibili")
    if errori:
        for nome, err in errori:
            print(f"   ⚠️  {nome}: {err[:80]}")
    print("=" * 65)
    if novita_totali:
        print("\n✅ PROSSIMI PASSI:")
        print("   1. Apri ogni link e verifica che sia un bando reale")
        print("   2. Se è un bando reale → aggiungi una riga in data/bandi.csv")
        print("   3. Esegui: python scripts/valida_e_archivia.py")


if __name__ == "__main__":
    main()
