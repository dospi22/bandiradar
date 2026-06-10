#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — Validazione + auto-archiviazione + freschezza (FLUSSO LOCALE)
═══════════════════════════════════════════════════════════════════════════

Va eseguito in LOCALE sul file data/bandi.csv, tipicamente dall'agente Claude
subito dopo aver aggiornato i bandi, PRIMA di caricare su GitHub con
Carica su GitHub.ps1.

Cosa fa:
  1. VALIDA data/bandi.csv (schema condiviso in scripts/schema.py):
       - campi obbligatori, ID univoci, date ISO, valori enum ammessi
       - errori critici -> esce con codice 1 (NON caricare finché non risolti)
       - warning -> li elenca ma non blocca
  2. VALIDA data/aziende.json (profili clienti):
       - codici mnemonici, P.IVA, ATECO, coerenza dimensione/dipendenti
       - solo i problemi strutturali bloccano; il resto è warning
  3. AUTO-ARCHIVIA i bandi con scadenza piu' vecchia di 30 giorni
     (e stato != Prorogato): li sposta da bandi.csv ad archivio.csv
  4. Genera data/last_sync.json per il badge "freschezza dati" della dashboard

Uso:
    python scripts/valida_e_archivia.py
    python scripts/valida_e_archivia.py --no-archivio   (salta l'archiviazione)
"""

import sys
import json
import argparse
from datetime import date, timedelta, datetime

# Schema e helper condivisi (unica fonte di verità)
# Nota: eseguendo `python scripts/valida_e_archivia.py` la cartella scripts/
# è già su sys.path, quindi l'import diretto funziona.
from schema import (
    ARCHIVE_AFTER_DAYS, BANDI, ARCHIVIO, AZIENDE, LASTSYNC, LINKSTAT,
    leggi_csv, scrivi_csv, valida_bandi, valida_aziende,
)


def conta_link(path):
    ok = ko = tot = 0
    try:
        with open(path, encoding='utf-8') as f:
            bandi = json.load(f).get('bandi', {})
        for b in bandi.values():
            tot += 1
            if b.get('status') == 'OK':
                ok += 1
            else:
                ko += 1
    except Exception:
        pass
    return ok, ko, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-archivio', action='store_true', help='Non spostare i bandi scaduti in archivio')
    args = ap.parse_args()

    oggi = date.today()

    rows, fields = leggi_csv(BANDI)
    if not rows:
        print(f"ERRORE: {BANDI} non trovato o vuoto")
        sys.exit(1)
    print(f"Caricati {len(rows)} bandi da data/bandi.csv")

    # ── 1. Validazione bandi.csv ─────────────────────────────────────
    critical, warnings = valida_bandi(rows)
    if warnings:
        print(f"\n{len(warnings)} warning (non bloccanti):")
        for w in warnings[:20]:
            print(f"  - {w}")
    if critical:
        print(f"\n❌ VALIDAZIONE FALLITA: {len(critical)} errori critici. NON caricare finché non risolti:")
        for e in critical:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ Validazione bandi.csv superata: nessun errore critico")

    # ── 2. Validazione aziende.json (profili clienti) ────────────────
    az_warnings = []
    try:
        with open(AZIENDE, encoding='utf-8') as f:
            dati_az = json.load(f)
        az_critical, az_warnings = valida_aziende(dati_az)
        if az_warnings:
            print(f"\n{len(az_warnings)} warning sui profili aziende (non bloccanti):")
            for w in az_warnings:
                print(f"  - {w}")
        if az_critical:
            print(f"\n❌ PROFILI AZIENDE: {len(az_critical)} errori critici:")
            for e in az_critical:
                print(f"  - {e}")
            sys.exit(1)
        print("✅ Validazione aziende.json superata")
    except FileNotFoundError:
        print("\n⚠️  data/aziende.json non trovato — salto la validazione profili")
    except json.JSONDecodeError as e:
        print(f"\n❌ data/aziende.json non è JSON valido: {e}")
        sys.exit(1)

    # ── 3. Auto-archiviazione ────────────────────────────────────────
    archiviati_ora = []
    if not args.no_archivio:
        cutoff = oggi - timedelta(days=ARCHIVE_AFTER_DAYS)
        attivi_rimasti, da_archiviare = [], []
        arch_rows, arch_fields = leggi_csv(ARCHIVIO)
        arch_ids = {r.get('ID', '') for r in arch_rows}

        for r in rows:
            fc = r.get('File CSV', '').strip()
            st = r.get('Stato', '').strip()
            scad_str = r.get('Scadenza', '').strip()
            if fc == 'Attivo' and st != 'Prorogato' and scad_str:
                try:
                    scad = datetime.strptime(scad_str, '%Y-%m-%d').date()
                except Exception:
                    scad = None
                if scad and scad < cutoff:
                    r['File CSV'] = 'Archivio'
                    da_archiviare.append(r)
                    archiviati_ora.append(r.get('ID', ''))
                    continue
            attivi_rimasti.append(r)

        if da_archiviare:
            # Unisci all'archivio esistente (no duplicati per ID)
            nuovo_arch = arch_rows + [r for r in da_archiviare if r.get('ID', '') not in arch_ids]
            # l'archivio usa sempre tutte le colonne di bandi.csv
            scrivi_csv(ARCHIVIO, nuovo_arch, fields)
            scrivi_csv(BANDI, attivi_rimasti, fields)
            rows = attivi_rimasti
            print(f"\n📦 Auto-archiviati {len(archiviati_ora)} bandi scaduti da oltre {ARCHIVE_AFTER_DAYS} giorni:")
            for rid in archiviati_ora:
                print(f"  - {rid}")
        else:
            print("\n📦 Nessun bando da auto-archiviare")

    # ── 4. Genera last_sync.json per il badge freschezza ─────────────
    attivi = [r for r in rows if r.get('File CSV', '').strip() == 'Attivo']
    arch_rows, _ = leggi_csv(ARCHIVIO)
    link_ok, link_ko, link_tot = conta_link(LINKSTAT)

    info = {
        'data':            oggi.isoformat(),
        'timestamp':       datetime.now().astimezone().isoformat(),
        'attivi':          len(attivi),
        'archivio':        len(arch_rows),
        'auto_archiviati': len(archiviati_ora),
        'warning_count':   len(warnings) + len(az_warnings),
        'link_ok':         link_ok,
        'link_ko':         link_ko,
        'link_totali':     link_tot,
        'origine':         'locale',
    }
    with open(LASTSYNC, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"\n🕐 data/last_sync.json aggiornato: {len(attivi)} attivi, {len(arch_rows)} archivio, "
          f"link {link_ok}/{link_tot} OK")
    print("\n✅ Pronto. Ora puoi caricare su GitHub con il file .bat.")


if __name__ == '__main__':
    main()
