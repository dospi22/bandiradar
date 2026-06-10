#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — schema.py
══════════════════════
UNICA FONTE DI VERITÀ per lo schema dati di BandiRadar.

Tutti gli script (valida_e_archivia.py, valida_raccomandazioni.py, ecc.)
importano costanti e funzioni da qui. Se lo schema CSV cambia, si aggiorna
SOLO questo file.

Contiene:
  - schema colonne bandi.csv (27 colonne, ordine esatto)
  - valori ammessi per i campi enum
  - helper comuni (date ISO, lettura/scrittura CSV)
  - validazione bandi.csv      -> valida_bandi(rows)
  - validazione aziende.json   -> valida_aziende(dati)
"""

import csv
import os
import re
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# SCHEMA CSV — 27 colonne obbligatorie, ordine esatto
# ─────────────────────────────────────────────────────────────────
COLONNE_CSV = [
    'ID', 'Nome bando', 'Ente erogatore', 'Livello', 'Categoria',
    'Categoria principale', 'Beneficiari', 'Tipo agevolazione',
    'Regime aiuto', 'Ambito geografico', 'Dettaglio geografico',
    'ATECO ammessi', 'Cumulabilità', 'Note cumulabilità',
    'Dotazione totale', 'Importo max beneficiario', 'Percentuale contributo',
    'Data apertura', 'Scadenza', 'Tipo scadenza', 'Stato', 'Priorità',
    'Link ufficiale', 'Data inserimento', 'Inserito da', 'File CSV',
    'Sintesi cliente',
]

REQUIRED_FIELDS = ['ID', 'Nome bando', 'Livello', 'Stato', 'File CSV']

VALID_LIVELLO  = {'Europeo', 'Nazionale', 'Regionale ER', 'Regionale'}
VALID_STATO    = {'Aperto', 'In arrivo', 'Prorogato', 'Sospeso'}
VALID_FILECSV  = {'Attivo', 'Archivio'}
VALID_PRIORITA = {'Alta', 'Media', 'Bassa', ''}
VALID_TIPOSCAD = {
    'Data fissa',
    'Sportello (fino a esaurimento fondi)',
    'Misura strutturale',
    'Anno fiscale',
    'Finestre periodiche',
    'Multidata/tappe',
    '',
}

# Formato ID: EU-2026-001 / IT-2026-001 / ER-2026-001
RE_ID_BANDO = re.compile(r'^(EU|IT|ER)-\d{4}-\d{3}$')

ARCHIVE_AFTER_DAYS = 30

# ─────────────────────────────────────────────────────────────────
# PERCORSI (relativi alla root del progetto; gli script stanno in scripts/)
# ─────────────────────────────────────────────────────────────────
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANDI    = os.path.join(ROOT, 'data', 'bandi.csv')
ARCHIVIO = os.path.join(ROOT, 'data', 'archivio.csv')
AZIENDE  = os.path.join(ROOT, 'data', 'aziende.json')
LASTSYNC = os.path.join(ROOT, 'data', 'last_sync.json')
LINKSTAT = os.path.join(ROOT, 'data', 'link_status.json')


# ─────────────────────────────────────────────────────────────────
# HELPER COMUNI
# ─────────────────────────────────────────────────────────────────
def is_iso_date(s):
    """True se la stringa è una data YYYY-MM-DD valida."""
    try:
        datetime.strptime(s.strip(), '%Y-%m-%d')
        return True
    except Exception:
        return False


def leggi_csv(path):
    """Legge un CSV con header. Ritorna (righe, nomi_colonne)."""
    if not os.path.exists(path):
        return [], []
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def scrivi_csv(path, righe, fields):
    """Scrive un CSV. utf-8-sig per compatibilità Excel."""
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(righe)


# ─────────────────────────────────────────────────────────────────
# VALIDAZIONE BANDI.CSV
# ─────────────────────────────────────────────────────────────────
def valida_bandi(rows):
    """
    Valida le righe di bandi.csv.
    Ritorna (critical, warnings): liste di messaggi.
    critical non vuota -> NON caricare su GitHub.
    """
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
            if not RE_ID_BANDO.match(rid):
                warnings.append(f"Riga {i}: ID '{rid}' non nel formato LIVELLO-ANNO-NNN")
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


# ─────────────────────────────────────────────────────────────────
# VALIDAZIONE AZIENDE.JSON (profili clienti)
# ─────────────────────────────────────────────────────────────────
RE_PIVA = re.compile(r'^\d{11}$')

def valida_aziende(dati):
    """
    Valida i profili in aziende.json.
    Ritorna (critical, warnings).
    Critical: solo problemi che rompono il matching o i file per-cliente.
    Warning: dati mancanti/incoerenti che degradano le raccomandazioni
             (es. ATECO vuoto -> criterio 'non verificabile').
    """
    critical, warnings = [], []
    aziende = dati.get('aziende', [])
    if not aziende:
        critical.append("aziende.json: nessun profilo presente")
        return critical, warnings

    codici_visti = set()
    for az in aziende:
        nome = az.get('nomeProfilo') or az.get('ragioneSociale') or '?'
        cod  = (az.get('codiceMnemonico') or '').strip()

        # codiceMnemonico: serve per i file raccomandazioni_<COD>.json
        if not cod:
            critical.append(f"[{nome}] codiceMnemonico mancante (serve per i file per-cliente)")
        elif cod in codici_visti:
            critical.append(f"[{nome}] codiceMnemonico duplicato '{cod}'")
        codici_visti.add(cod)

        # Campi necessari al matching geografico/dimensionale
        for fld in ('ragioneSociale', 'regione', 'dimensione'):
            if not (az.get(fld) or '').strip():
                warnings.append(f"[{nome}] campo '{fld}' vuoto")

        # ATECO — errore comune n.5: senza ATECO il matching è degradato
        if not (az.get('ateco') or '').strip():
            warnings.append(f"[{nome}] ATECO vuoto -> criterio settoriale 'non verificabile' nel matching")

        # P.IVA: 11 cifre
        piva = (az.get('piva') or '').strip()
        if piva and not RE_PIVA.match(piva):
            warnings.append(f"[{nome}] P.IVA '{piva}' non valida (servono 11 cifre) — DA VERIFICARE")
        elif not piva:
            warnings.append(f"[{nome}] P.IVA mancante")

        # Coerenza dimensione <-> dipendenti
        dim  = (az.get('dimensione') or '').lower()
        hasd = (az.get('hasDipendenti') or '').lower()
        forza = (az.get('forzaLavoro') or '').lower()
        if 'microimpresa' in dim and hasd.startswith('s'):
            # micro = <10 dipendenti: se dichiara 10-49 dipendenti è incoerente
            if '10 e 49' in hasd or '50' in hasd:
                warnings.append(f"[{nome}] incoerenza: Microimpresa ma dipendenti dichiarati >= 10")
        if hasd.startswith('no') and 'dipendent' in forza and 'p.iva' not in forza:
            warnings.append(f"[{nome}] incoerenza: hasDipendenti=No ma forzaLavoro indica dipendenti")

    return critical, warnings
