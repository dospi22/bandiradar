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
    # bandi.gov.it RIMOSSO il 2026-06-12: dominio non più risolvibile (dismesso).
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
    {
        "id": "simest",
        "nome": "SIMEST — Comunicati (Fondo 394 e internazionalizzazione)",
        "livello": "Nazionale",
        "url_rss": "https://www.simest.it/media/comunicati-stampa/feed",  # feed WordPress verificato 2026-06-12
        "url_web": "https://www.simest.it/media/comunicati-stampa/",
        "metodo": "RSS",
        "frequenza": "settimanale",
        "note": "Aperture/chiusure Fondo 394 annunciate qui. Il sito può rispondere 403 (WAF) da GitHub Actions: in tal caso lo stato atteso è BLOCCATO, non rotto.",
    },
    {
        "id": "inail-isi",
        "nome": "INAIL — Incentivi alle imprese (Bando ISI)",
        "livello": "Nazionale",
        "url_rss": "",  # portale interamente JS dal restyling: HTML vuoto via fetch (verificato 2026-06-12) -> check manuale
        "url_web": "https://www.inail.it/portale/prevenzione-e-sicurezza/it/prevenzione-e-sicurezza/finanziamenti-per-la-sicurezza/incentivi-alle-imprese.html",
        "metodo": "Check manuale",
        "frequenza": "mensile",
        "note": "Bando ISI annuale. Per la ricerca automatica usare Google: \"bando ISI\" site:inail.it (già nella skill di ricerca).",
    },
    {
        "id": "agricoltura-er",
        "nome": "Regione ER — Agricoltura (PSR/CSR, agroalimentare)",
        "livello": "Regionale ER",
        "url_rss": "https://agricoltura.regione.emilia-romagna.it/RSS",  # feed Plone verificato 2026-06-12
        "url_web": "https://agricoltura.regione.emilia-romagna.it/bandi",
        "metodo": "RSS",
        "frequenza": "settimanale",
        "note": "Bandi Sviluppo Rurale CSR 2023-2027, agroalimentare, agriturismo. Il feed copre tutto il sito: filtrare con le keywords.",
    },
    {
        "id": "ministero-turismo",
        "nome": "Ministero del Turismo — Avvisi e incentivi",
        "livello": "Nazionale",
        "url_rss": "https://www.ministeroturismo.gov.it/feed/",  # feed WordPress verificato 2026-06-12
        "url_web": "https://www.ministeroturismo.gov.it/",
        "metodo": "RSS",
        "frequenza": "settimanale",
        "note": "Avvisi e incentivi turismo/HORECA (clienti Livello 2). Il feed copre tutte le news: filtrare con le keywords.",
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
    # simest spostato in FONTI_RSS il 2026-06-12 (trovato feed WordPress nativo).
    # inail-isi spostato in FONTI_RSS come Check manuale il 2026-06-12 (portale JS, diff impossibile).
    {
        "id": "gse-imprese",
        "nome": "GSE — Servizi e incentivi per le imprese",
        "livello": "Nazionale",
        "url_web": "https://www.gse.it/servizi-per-te/imprese",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Incentivi energia (FER, CER, efficienza). Può rispondere 403 (WAF anti-bot) da GitHub Actions: pagina raggiungibile da browser, stato atteso BLOCCATO.",
    },
    {
        "id": "euipo-sme-fund",
        "nome": "EUIPO — SME Fund (voucher marchi e brevetti)",
        "livello": "Europeo",
        "url_web": "https://www.euipo.europa.eu/it/sme-corner/sme-fund",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Finestra 2026: 2 feb - 4 dic. Può rispondere 403 (WAF anti-bot) da GitHub Actions: pagina raggiungibile da browser, stato atteso BLOCCATO.",
    },
    {
        "id": "eber-artigianato",
        "nome": "EBER — Ente Bilaterale Artigianato ER (sviluppo imprenditoriale)",
        "livello": "Regionale ER",
        "url_web": "https://www.eber.org/Attivita/sviluppo-imprenditoriale",
        "metodo": "Diff pagina",
        "frequenza": "mensile",
        "note": "Contributi e attività per imprese artigiane ER (clienti Livello 2 artigianato). Sito server-side, verificato 2026-06-12.",
    },
    {
        "id": "artigiancredito",
        "nome": "Artigiancredito — News (Fondo Starter, Energia, EuReCa, Microcredito ER)",
        "livello": "Regionale ER",
        "url_web": "https://www.artigiancredito.it/it-it/news",
        "metodo": "Diff pagina",
        "frequenza": "settimanale",
        "note": "Gestore dei fondi multiscopo Regione ER: riaperture Fondo Starter/Energia/EuReCa annunciate qui. Verificato 2026-06-12.",
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
    # settori clienti Livello 2 (aggiunti 2026-06-12)
    "turismo", "horeca", "ristorazione", "ricettiv", "agriturismo",
    "artigian", "agroalimentare", "psr", "csr", "commercio",
    "fondo starter", "fondo energia", "eureca", "microcredito",
]

KEYWORDS_NEGATIVI = [
    "webinar", "evento", "conferenza", "seminario",
    "consultazione pubblica", "bozza", "annuncio generico",
    "comunicato stampa", "nota stampa",
]
