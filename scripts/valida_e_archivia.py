#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — Validazione + auto-archiviazione + freschezza (FLUSSO LOCALE)
═══════════════════════════════════════════════════════════════════════════

Va eseguito in LOCALE sul file data/bandi.csv, tipicamente dall'agente Claude
subito dopo aver aggiornato i bandi, PRIMA di caricare su GitHub con
Carica su GitHub.ps1.

Cosa fa:
  1. VALIDA data/bandi.csv (stessi controlli di qualità):
       - campi obbligatori, ID univoci, date ISO, valori enum ammessi
       - errori critici -> esce con codice 1 (NON caricare finché non risolti)
       - warning -> li elenca ma non blocca
  2. AUTO-ARCHIVIA i bandi con scadenza piu' vecchia di 30 giorni
     (e stato != Prorogato): li sposta da bandi.csv ad archivio.csv
  3. Genera data/last_sync.json per il badge "freschezza dati" della dashboard

Uso:
    python scripts/valida_e_archivia.py
    python scripts/valida_e_archivia.py --no-archivio   (salta l'archiviazione)
"""

import os
import sys
import csv
import json
import argparse
from datetime import date, timedelta, datetime

# ─── Costanti di validazione (identiche alla dashboard) ──────────────────────
REQUIRED_FIELDS = ['ID', 'Nome bando', 'Livello', 'Stato', 'File CSV']
VALID_LIVELLO   = {'Europeo', 'Nazionale', 'Regionale ER', 'Regionale'}
VALID_STATO     = {'Aperto', 'In arrivo', 'Prorogato', 'Sospeso'}
VALID_FILECSV   = {'Attivo', 'Archivio'}
VALID_PRIORITA  = {'Alta', 'Media', 'Bassa', ''}
VALID_TIPOSCAD  = {
    'Data fissa',
    'Sportello (fino a esaurimento fondi)',
    'Misura strutturale',
    'Anno fiscale',
    'Finestre periodiche',
    'Multidata/tappe',
    '',
}
ARCHIVE_AFTER_DAYS = 30

# Percorsi relativi alla root del progetto (lo script sta in scripts/)
ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANDI     = os.path.join(ROOT, 'data', 'bandi.csv')
ARCHIVIO  = os.path.join(ROOT, 'data', 'archivio.csv')
LASTSYNC  = os.path.join(ROOT, 'data', 'last_sync.json')
LINKSTAT  = os.path.join(ROOT, 'data', 'link_status.json')


def is_iso_date(s):
    try:
        datetime.strptime(s.strip(), '%Y-%m-%d')
        return True
    except Exception:
        return False


def leggi_csv(path):
    if not os.path.exists(path):
        return [], []
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def scrivi_csv(path, righe, fields):
    # utf-8-sig per compatibilità Excel
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(righe)


def valida(rows):
    critical, warnings, ids_seen = [], [], set()
    for i, row in enumerate(rows, 2):  # riga 1 = header
        for fld in REQUIRED_FIELDS:
            if not row.get(fld, '').strip():
                critical.append(f"Riga {i}: campo obbligatorio vuoto '{fld}'")
        rid = row.get('ID', '').strip()
        if rid:
            if rid in ids_seen:
                critical.append(f"Riga {i}: ID duplicato '{rid}'")
            ids_seen.add(rid)
        liv = row.get('Livello', '').strip()
        if liv and liv not in VALID_LIVELLO:
            critical.append(f"Riga {i} ({rid}): Livello non valido '{liv}'")
        st = row.get('Stato', '').strip()
        if st and st not in VALID_STATO:
            critical.append(f"Riga {i} ({rid}): Stato non valido '{st}'")
        fc = row.get('File CSV', '').strip()
        if fc and fc not in VALID_FILECSV:
            critical.append(f"Riga {i} ({rid}): File CSV non valido '{fc}'")
        pr = row.get('Priorità', '').strip()
        if pr and pr not in VALID_PRIORITA:
            warnings.append(f"Riga {i} ({rid}): Priorità non valida '{pr}'")
        ts = row.get('Tipo scadenza', '').strip()
        if ts and ts not in VALID_TIPOSCAD:
            warnings.append(f"Riga {i} ({rid}): Tipo scadenza non valido '{ts}'")
        for df in ('Scadenza', 'Data apertura', 'Data inserimento'):
            v = row.get(df, '').strip()
            if v and not is_iso_date(v):
                critical.append(f"Riga {i} ({rid}): {df} non in formato YYYY-MM-DD: '{v}'")
    return critical, warnings


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

    # ── 1. Validazione ───────────────────────────────────────────────
    critical, warnings = valida(rows)
    if warnings:
        print(f"\n{len(warnings)} warning (non bloccanti):")
        for w in warnings[:20]:
            print(f"  - {w}")
    if critical:
        print(f"\n❌ VALIDAZIONE FALLITA: {len(critical)} errori critici. NON caricare finché non risolti:")
        for e in critical:
            print(f"  - {e}")
        sys.exit(1)
    print("✅ Validazione superata: nessun errore critico")

    # ── 2. Auto-archiviazione ────────────────────────────────────────
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
            af = arch_fields if arch_fields else fields
            # assicura che l'archivio abbia tutte le colonne di bandi.csv
            af = fields
            scrivi_csv(ARCHIVIO, nuovo_arch, af)
            scrivi_csv(BANDI, attivi_rimasti, fields)
            rows = attivi_rimasti
            print(f"\n📦 Auto-archiviati {len(archiviati_ora)} bandi scaduti da oltre {ARCHIVE_AFTER_DAYS} giorni:")
            for rid in archiviati_ora:
                print(f"  - {rid}")
        else:
            print("\n📦 Nessun bando da auto-archiviare")

    # ── 3. Genera last_sync.json per il badge freschezza ─────────────
    attivi = [r for r in rows if r.get('File CSV', '').strip() == 'Attivo']
    arch_rows, _ = leggi_csv(ARCHIVIO)
    link_ok, link_ko, link_tot = conta_link(LINKSTAT)

    info = {
        'data':            oggi.isoformat(),
        'timestamp':       datetime.now().astimezone().isoformat(),
        'attivi':          len(attivi),
        'archivio':        len(arch_rows),
        'auto_archiviati': len(archiviati_ora),
        'warning_count':   len(warnings),
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
