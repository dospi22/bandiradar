#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BandiRadar — fonti.py
═════════════════════
UNICA FONTE DI VERITÀ per l'elenco delle fonti monitorate.

Importato da:
  - monitor_rss.py      (fonti con feed RSS)
  - monitor_pagine.py   (fonti senza RSS -> diff settimanale della pagina)
  - verifica_fonti.py   (health-check di TUTTE le fonti)

Per aggiungere una fonte si modifica SOLO questo file.

Campi:
  id        slug univoco (usato nei file di stato/snapshot)
  nome      nome leggibile
  livello   Europeo / Nazionale / Regionale ER / Nazionale-UE
  url_rss   feed RSS (solo FONTI_RSS; '' = nessun feed)
  url_web   pagina web di riferimento
  metodo    RSS / Diff pagina / Check manuale
"""

# ─────────────────────────────────────────────────────────────────
# FONTI CON FEED RSS (lette da monitor_rss.py)
# ─────────────────────────────────────────────────────────────────
FONTI_RSS = [
    {
        "id": "mimit",
        "nome": "MIMIT — Aggiornamenti sugli incentivi",
        "livello": "Nazionale",
        "url_rss": "https://www.mimit.gov.it/index.php/it/incentivi-aggiornamenti?format=feed&type=rss",
        "url_web": "https://www.mimit.gov.it/it/incentivi",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "id": "incentivi-gov",
        "nome": "Incentivi.gov — Catalogo nazionale",
        "livello": "Nazionale",
        "url_rss": "",  # nessun RSS, catalogo JS -> check manuale
        "url_web": "https://www.incentivi.gov.it/it/catalogo",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "id": "bandi-gov",
        "nome": "Bandi.gov.it — Portale nazionale (DOMINIO NON RAGGIUNGIBILE)",
        "livello": "Nazionale",
        "url_rss": "",  # dominio non risolvibile al 2026-06-11 -> probabilmente dismesso, valutare rimozione
        "url_web": "https://bandi.gov.it",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "id": "euknow",
        "nome": "Euknow — Bandi UE e nazionali",
        "livello": "Nazionale/UE",
        "url_rss": "https://euknow.it/feed/",
        "url_web": "https://euknow.it",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "id": "regione-er-imprese",
        "nome": "Regione Emilia-Romagna — Finanziamenti imprese",
        "livello": "Regionale ER",
        "url_rss": "https://imprese.regione.emilia-romagna.it/RSS",
        "url_web": "https://imprese.regione.emilia-romagna.it/bandi",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "id": "regione-er-sociale",
        "nome": "Regione ER — Sociale e Terzo Settore",
        "livello": "Regionale ER",
        "url_rss": "",
        "url_web": "https://sociale.regione.emilia-romagna.it/bandi",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "id": "art-er",
        "nome": "ART-ER — Bandi e opportunità",
        "livello": "Regionale ER",
        "url_rss": "",  # feed morto (404, verificato 2026-06-11); vedi anche fonte er-startup
        "url_web": "https://www.art-er.it/bandi/",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
    {
        "id": "infobandi-csvnet",
        "nome": "INFOBANDI CSVNET — Terzo Settore",
        "livello": "Nazionale",
        "url_rss": "https://infobandi.csvnet.it/feed",
        "url_web": "https://infobandi.csvnet.it",
        "metodo": "RSS",
        "frequenza": "bisettimanale",
    },
    {
        "id": "apre",
        "nome": "APRE — Punto di contatto nazionale Horizon Europe",
        "livello": "Europeo",
        "url_rss": "https://apre.it/feed/",
        "url_web": "https://apre.it",
        "metodo": "RSS",
        "frequenza": "settimanale",
    },
    {
        "id": "fondimpresa",
        "nome": "Fondimpresa — Avvisi formazione finanziata",
        "livello": "Nazionale",
        "url_rss": "",  # sito renderizzato in JS -> check manuale
        "url_web": "https://www.fondimpresa.it/fondimpresa-per-le-aziende/avvisi",
        "metodo": "Check manuale",
        "frequenza": "mensile",
    },
    {
        "id": "gazzetta-ufficiale",
        "nome": "Gazzetta Ufficiale — Serie Generale (nuovi decreti)",
        "livello": "Nazionale",
        "url_rss": "",  # nessun feed affidabile, pagina cambia ogni giorno -> check manuale
        "url_web": "https://www.gazzettaufficiale.it",
        "metodo": "Check manuale",
        "frequenza": "settimanale",
    },
]

# ─────────────────────────────────────────────────────────────────
# FONTI SENZA RSS — monitorate con diff settimanale della pagina
# (lette da monitor_pagine.py; URL verificati il 2026-06-10)
# ─────────────────────────────────────────────────────────────────
FONTI_PAGINE = [
    {
        "id": "invitalia",
        "nome": "Invitalia — Incentivi e strumenti",
        "livello": "Nazionale",
        "url_web": "https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Feed RSS dismesso (404) -> diff sul catalogo incentivi; URL verificato 2026-06-11",
    },
    {
        "id": "cciaa-romagna",
        "nome": "CCIAA Romagna (Forlì-Cesena e Rimini) — Finanziamenti",
        "livello": "Regionale ER",
        "url_web": "https://www.romagna.camcom.it/it/opportunita/finanziamenti-1",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Bandi camerali (voucher digitali, fiere, doppia transizione) — molto rilevanti per microimprese di Rimini/FC",
    },
    {
        "id": "fesr-er",
        "nome": "FESR Emilia-Romagna — Bandi 2021-2027",
        "livello": "Regionale ER",
        "url_web": "https://fesr.regione.emilia-romagna.it/opportunita/opportunita-di-finanziamento/bandi-21-27",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Digitalizzazione, R&S, internazionalizzazione, energia",
    },
    {
        "id": "simest",
        "nome": "SIMEST — Comunicati (Fondo 394 e internazionalizzazione)",
        "livello": "Nazionale",
        "url_web": "https://www.simest.it/media/comunicati-stampa/",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Aperture/chiusure Fondo 394 annunciate qui",
    },
    {
        "id": "inail-isi",
        "nome": "INAIL — Incentivi alle imprese (Bando ISI)",
        "livello": "Nazionale",
        "url_web": "https://www.inail.it/portale/prevenzione-e-sicurezza/it/prevenzione-e-sicurezza/finanziamenti-per-la-sicurezza/incentivi-alle-imprese.html",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Bando ISI annuale, sicurezza sul lavoro",
    },
    {
        "id": "gse-imprese",
        "nome": "GSE — Servizi e incentivi per le imprese",
        "livello": "Nazionale",
        "url_web": "https://www.gse.it/servizi-per-te/imprese",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Incentivi energia (FER, CER, efficienza)",
    },
    {
        "id": "euipo-sme-fund",
        "nome": "EUIPO — SME Fund (voucher marchi e brevetti)",
        "livello": "Europeo",
        "url_web": "https://www.euipo.europa.eu/it/sme-corner/sme-fund",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Finestra annuale: nel 2026 dal 2 feb al 4 dic",
    },
    {
        "id": "er-startup",
        "nome": "EmiliaRomagnaStartUp (ART-ER) — Bandi e call",
        "livello": "Regionale ER",
        "url_web": "https://www.emiliaromagnastartup.it/it/bandi",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Bandi/call per startup e PMI innovative ER (ER2DIGIT, Start Cup, call internazionali) — URL verificato 2026-06-11",
    },
]

# Parole chiave per filtrare i contenuti rilevanti (condivise)
KEYWORDS_POSITIVI = [
    "bando", "agevolazione", "incentivo", "contributo", "finanziamento",
    "credito d'imposta", "voucher", "fondo perduto", "sportello", "aperto",
    "pmi", "impresa", "startup", "innovazione", "digitale", "sostenibilità",
    "internazionalizzazione", "ricerca", "sviluppo", "emilia-romagna",
    "mimit", "invitalia", "simest", "regione er", "por-fesr", "fse",
    "horizon", "eic", "life", "interreg", "pnrr", "fesr", "sme fund",
    "doppia transizione", "fiere", "isi",
]

KEYWORDS_NEGATIVI = [
    "webinar", "evento", "conferenza", "seminario",
    "consultazione pubblica", "bozza", "annuncio generico",
    "comunicato stampa", "nota stampa",
]
