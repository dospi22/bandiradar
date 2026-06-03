#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invia_digest.py
===============
Invia email settimanale personalizzata per ogni cliente BandiRadar.
Viene chiamato da .github/workflows/weekly-digest.yml

Logica:
  - Per ogni azienda in data/aziende.json con campo "email" valorizzato
  - Legge data/raccomandazioni_[CODICE].json
  - Filtra bandi nuovi/aggiornati dall'ultima esecuzione (data/ultimo_digest.json)
  - Se ci sono bandi nuovi -> invia email HTML
  - Se nessuna novita -> salta silenziosamente
  - Se errore SMTP -> logga ma continua con gli altri clienti
"""

import csv
import json
import os
import sys
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── Configurazione ────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
DATA_DIR  = BASE_DIR / "data"
TODAY     = date.today()
UNA_SETTIMANA_FA = TODAY - timedelta(days=7)

SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


# ── Helper ────────────────────────────────────────────────────────────────────
def parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip())
    except ValueError:
        return None


def fmt_euro(s):
    try:
        n = float(s) if s else 0
        if n <= 0:
            return "n.d."
        if n >= 1e9:
            return "EUR {:.1f} Mld".format(n / 1e9)
        if n >= 1e6:
            return "EUR {:d} Mln".format(int(n / 1e6))
        if n >= 1e3:
            return "EUR {:d}K".format(int(n / 1e3))
        return "EUR {:,}".format(int(n))
    except Exception:
        return "n.d."


def is_link_rotto(bid, link_status):
    info = link_status.get(bid, {})
    return isinstance(info, dict) and info.get("status") not in (None, "OK", "ok")


def invia_email(dest, oggetto, html):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = oggetto
        msg["From"]    = "BandiRadar <{}>".format(SMTP_USER)
        msg["To"]      = dest
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP("smtp.gmail.com", 587) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, [dest], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


# ── Carica dati base ──────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  BandiRadar -- Digest settimanale per-cliente")
    print("=" * 55)

    if not SMTP_USER or not SMTP_PASS:
        print("ERRORE: SMTP_USER o SMTP_PASS non configurati nei secrets GitHub")
        sys.exit(1)

    # bandi.csv
    bandi_map = {}
    try:
        with open(DATA_DIR / "bandi.csv", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                bid = row.get("ID", "").strip()
                if bid:
                    bandi_map[bid] = row
    except FileNotFoundError:
        print("ERRORE: data/bandi.csv non trovato")
        sys.exit(1)

    # link_status.json
    link_status = {}
    try:
        with open(DATA_DIR / "link_status.json", encoding="utf-8") as f:
            link_status = json.load(f)
    except Exception:
        pass

    # aziende.json
    aziende = []
    try:
        with open(DATA_DIR / "aziende.json", encoding="utf-8") as f:
            raw = f.read().rstrip("\x00")
            data = json.loads(raw)
            aziende = data.get("aziende", data) if isinstance(data, dict) else data
    except FileNotFoundError:
        print("ERRORE: data/aziende.json non trovato")
        sys.exit(1)

    # ultimo_digest.json
    ultima_data = UNA_SETTIMANA_FA
    try:
        with open(DATA_DIR / "ultimo_digest.json", encoding="utf-8") as f:
            ud = json.load(f)
            ultima_data = parse_date(ud.get("data", "")) or UNA_SETTIMANA_FA
    except Exception:
        pass

    print("Bandi nel CSV   : {}".format(len(bandi_map)))
    print("Clienti         : {}".format(len(aziende)))
    print("Bandi nuovi da  : {}".format(ultima_data))
    print()

    # ── Ciclo per cliente ─────────────────────────────────────────────────────
    inviati = 0
    saltati = 0
    errori  = []

    for az in aziende:
        codice = az.get("codiceMnemonico", "")
        nome   = az.get("nomeProfilo") or az.get("ragioneSociale") or codice
        email  = (az.get("email") or "").strip()

        if not email or not codice:
            saltati += 1
            motivo = "email mancante" if not email else "codiceMnemonico mancante"
            print("[SKIP] {} -- {}".format(nome, motivo))
            continue

        racc_file = DATA_DIR / "raccomandazioni_{}.json".format(codice)
        if not racc_file.exists():
            saltati += 1
            print("[SKIP] {} -- nessun file raccomandazioni_{}.json".format(nome, codice))
            continue

        try:
            with open(racc_file, encoding="utf-8") as f:
                racc_data = json.load(f)
        except Exception as e:
            print("[ERR]  {} -- impossibile leggere {}: {}".format(nome, racc_file.name, e))
            continue

        # Estrai raccomandazioni
        racc_items = []
        for az_block in racc_data.get("aziende", []):
            racc_items.extend(az_block.get("raccomandazioni", []))

        # Filtra bandi nuovi dall'ultima esecuzione
        bandi_nuovi = []
        for item in racc_items:
            bid  = item.get("id", "")
            brow = bandi_map.get(bid)
            if not brow:
                continue
            d_ins = parse_date(brow.get("Data inserimento", ""))
            d_upd = parse_date(brow.get("Ultimo aggiornamento", ""))
            d_max = max(filter(None, [d_ins, d_upd]), default=None)
            if d_max and d_max > ultima_data:
                bandi_nuovi.append((item, brow))

        if not bandi_nuovi:
            saltati += 1
            print("[SKIP] {} ({}) -- nessun bando nuovo questa settimana".format(nome, email))
            continue

        print("[SEND] {} ({}) -- {} bandi nuovi".format(nome, email, len(bandi_nuovi)))

        # ── Componi HTML ──────────────────────────────────────────────────────
        oggi_it = TODAY.strftime("%-d %B %Y")

        righe_bandi = ""
        for item, brow in bandi_nuovi:
            bid      = item.get("id", "")
            nome_b   = item.get("nome") or brow.get("Nome bando", "")
            ente     = brow.get("Ente erogatore", "")
            link     = brow.get("Link ufficiale", "")
            importo  = fmt_euro(brow.get("Importo max beneficiario", ""))
            perc     = brow.get("Percentuale contributo", "")
            tipo     = brow.get("Tipo agevolazione", "").split("|")[0].strip()
            scad_d   = parse_date(brow.get("Scadenza", ""))
            motiv    = item.get("motivazioneEstesa") or item.get("motivazione", "")
            rotto    = is_link_rotto(bid, link_status)

            if scad_d:
                giorni = (scad_d - TODAY).days
                if giorni <= 30:
                    badge = '<span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:bold;background:#fee2e2;color:#991b1b">Scade in {} giorni ({})</span>'.format(giorni, scad_d.strftime("%-d/%m/%Y"))
                else:
                    badge = '<span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:bold;background:#fef3c7;color:#92400e">Scade il {} ({} giorni)</span>'.format(scad_d.strftime("%-d/%m/%Y"), giorni)
            else:
                badge = '<span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:bold;background:#d1fae5;color:#065f46">Sportello aperto</span>'

            contributo = importo
            if perc:
                contributo += " -- {}%".format(perc)

            if rotto:
                link_html = '<div style="margin-top:10px;display:inline-block;background:#fef3c7;color:#92400e;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:bold;border:1px solid #fde68a">Link ufficiale temporaneamente non raggiungibile -- contattami per i dettagli</div>'
            else:
                link_html = '<a style="display:inline-block;margin-top:10px;background:#1e40af;color:#fff;padding:7px 16px;border-radius:5px;text-decoration:none;font-size:12px;font-weight:bold" href="{}">Vai al bando ufficiale</a>'.format(link)

            motiv_html = ""
            if motiv:
                motiv_html = '<div style="font-size:12px;color:#374151;font-style:italic;margin-top:6px">"' + motiv + '"</div>'

            righe_bandi += """
<div style="margin:0 20px 10px;border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;background:#f9fafb">
  <div style="font-size:14px;font-weight:bold;color:#111827;margin:0 0 2px">{nome_b}</div>
  <div style="font-size:12px;color:#6b7280;margin:0 0 8px">{ente}</div>
  {badge}
  <div style="font-size:12px;color:#374151;margin-top:8px">{contributo} &nbsp;·&nbsp; {tipo}</div>
  {motiv_html}
  {link_html}
</div>""".format(
                nome_b=nome_b, ente=ente, badge=badge,
                contributo=contributo, tipo=tipo,
                motiv_html=motiv_html, link_html=link_html
            )

        html = """<!DOCTYPE html>
<html lang="it">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;color:#111827">
<div style="max-width:620px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb">
  <div style="background:#1e40af;padding:24px 28px">
    <div style="color:#fff;font-size:20px;font-weight:bold;margin:0">BandiRadar -- Novita della settimana</div>
    <div style="color:#bfdbfe;font-size:13px;margin:4px 0 0">{oggi_it} &nbsp;·&nbsp; Aggiornamento per {nome}</div>
  </div>
  <div style="padding:20px 28px 8px;font-size:14px;color:#374151;line-height:1.6">
    Ciao,<br>
    questa settimana ci sono <strong>{n} nuovi bandi o aggiornamenti</strong> rilevanti per <strong>{nome}</strong>.
  </div>
  <div style="padding:4px 28px 10px;font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:0.7px;color:#9ca3af">Bandi consigliati</div>
  {righe_bandi}
  <div style="padding:18px 28px;background:#f3f4f6;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;line-height:1.8">
    Per maggiori informazioni o per procedere con la domanda, rispondimi a questa email.<br>
    <strong>Alex</strong> -- Consulente di finanza agevolata<br><br>
    BandiRadar · Aggiornamento automatico del {oggi_it} · Non rispondere direttamente a questa email
  </div>
</div>
</body>
</html>""".format(oggi_it=oggi_it, nome=nome, n=len(bandi_nuovi), righe_bandi=righe_bandi)

        oggetto = "BandiRadar {data} -- {n} novita per {nome}".format(
            data=TODAY.strftime("%d/%m/%Y"),
            n=len(bandi_nuovi),
            nome=nome
        )

        ok, err = invia_email(email, oggetto, html)
        if ok:
            inviati += 1
            print("  OK Inviata a {}".format(email))
        else:
            errori.append("{} ({}): {}".format(nome, email, err))
            print("  ERRORE invio a {}: {}".format(email, err))

    # ── Aggiorna ultimo_digest.json ───────────────────────────────────────────
    try:
        with open(DATA_DIR / "ultimo_digest.json", "w", encoding="utf-8") as f:
            json.dump({"data": TODAY.isoformat(), "inviati": inviati}, f, indent=2)
    except Exception as e:
        print("WARN: impossibile aggiornare ultimo_digest.json: {}".format(e))

    # ── Riepilogo ─────────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("  Inviate: {} | Saltate: {} | Errori: {}".format(inviati, saltati, len(errori)))
    if errori:
        print("  ERRORI:")
        for e in errori:
            print("    - {}".format(e))
        sys.exit(1)
    else:
        print("  OK -- Digest completato.")
    print("=" * 55)


if __name__ == "__main__":
    main()
