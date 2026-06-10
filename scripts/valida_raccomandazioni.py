"""
valida_raccomandazioni.py
=========================
Legge bandi.csv e tutti i file raccomandazioni_*.json, verifica che:
  - ogni ID raccomandato esista nel CSV
  - nessun bando raccomandato sia scaduto
  - nessun bando abbia link rotto (se link_status.json disponibile)

Rimuove automaticamente i record non validi e salva i JSON puliti.

Uso:
    python scripts/valida_raccomandazioni.py
"""

import json
import sys
import glob
from datetime import date
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
_cwd        = Path.cwd()

if (_cwd / "data" / "bandi.csv").exists():
    BASE_DIR = _cwd
else:
    BASE_DIR = _script_dir.parent

# Helper condivisi (scripts/schema.py = unica fonte di verità per lo schema)
sys.path.insert(0, str(_script_dir))
from schema import leggi_csv

CSV_PATH  = BASE_DIR / "data" / "bandi.csv"
LINK_PATH = BASE_DIR / "data" / "link_status.json"
TODAY     = date.today()


def carica_bandi(csv_path):
    rows, _ = leggi_csv(str(csv_path))
    return {row["ID"].strip(): row for row in rows if row.get("ID", "").strip()}


def carica_link_ko(link_path):
    if not link_path.exists():
        return set()
    try:
        with open(link_path, encoding="utf-8") as f:
            data = json.load(f)
        bandi_status = data.get("bandi", data)
        return {bid for bid, info in bandi_status.items()
                if isinstance(info, dict) and info.get("status") not in (None, "OK", "ok")}
    except Exception:
        return set()


def valida_file(json_path, bandi_map, link_ko, salva=True):
    if not json_path.exists():
        raise FileNotFoundError(f"File non trovato: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        dati = json.load(f)

    rimossi    = []
    scaduti    = []
    link_rotti = []
    mantenuti  = []
    modificato = False

    for azienda in dati.get("aziende", []):
        az_id = azienda.get("idAzienda", "?")
        racc_originali = azienda.get("raccomandazioni", [])
        racc_valide = []

        for r in racc_originali:
            bid = r.get("id", "")

            # 1. ID inesistente nel CSV
            if bid not in bandi_map:
                rimossi.append(bid)
                modificato = True
                print(f"  [RIMOSSO - ID inesistente] {bid} (azienda: {az_id})")
                continue

            bando = bandi_map[bid]

            # 2. Bando scaduto
            scad_str = bando.get("Scadenza", "").strip()
            if scad_str:
                try:
                    scad_date = date.fromisoformat(scad_str)
                    if scad_date < TODAY:
                        scaduti.append(bid)
                        modificato = True
                        print(f"  [RIMOSSO - scaduto il {scad_str}] {bid} | {bando.get('Nome bando','')[:50]}")
                        continue
                except ValueError:
                    pass

            # 3. Link rotto
            if bid in link_ko:
                link_rotti.append(bid)
                modificato = True
                print(f"  [RIMOSSO - link rotto] {bid} | {bando.get('Nome bando','')[:50]}")
                continue

            racc_valide.append(r)
            mantenuti.append(bid)

        azienda["raccomandazioni"] = racc_valide

    if salva and modificato:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        print(f"  -> File aggiornato: {json_path.name}")

    return {
        "ok":         not (rimossi or scaduti or link_rotti),
        "rimossi":    rimossi,
        "scaduti":    scaduti,
        "link_rotti": link_rotti,
        "mantenuti":  mantenuti,
        "dati":       dati,
    }


def trova_file_raccomandazioni(base_dir):
    pattern = str(base_dir / "data" / "raccomandazioni_*.json")
    files = [Path(p) for p in glob.glob(pattern)]
    legacy = base_dir / "data" / "raccomandazioni.json"
    if legacy.exists():
        files.append(legacy)
    return sorted(files)


def main():
    print("=" * 60)
    print("  BandiRadar -- Validazione raccomandazioni per-cliente")
    print("=" * 60)

    if not CSV_PATH.exists():
        print(f"\nERRORE: {CSV_PATH} non trovato")
        sys.exit(1)

    bandi_map = carica_bandi(CSV_PATH)
    link_ko   = carica_link_ko(LINK_PATH)
    files     = trova_file_raccomandazioni(BASE_DIR)

    if not files:
        print("\n  Nessun file raccomandazioni trovato in data/")
        sys.exit(0)

    print(f"\n  Bandi nel CSV   : {len(bandi_map)}")
    print(f"  Link KO noti    : {len(link_ko)}")
    print(f"  File da validare: {len(files)}")
    print(f"  Data oggi       : {TODAY}")
    print()

    totale_ok       = True
    tot_rimossi     = 0
    tot_scaduti     = 0
    tot_rotti       = 0
    tot_mantenuti   = 0

    for json_path in files:
        print(f"-- {json_path.name} --")
        try:
            res = valida_file(json_path, bandi_map, link_ko)
        except FileNotFoundError as e:
            print(f"  ERRORE: {e}")
            continue

        n_ok  = len(res["mantenuti"])
        n_rim = len(res["rimossi"])
        n_sca = len(res["scaduti"])
        n_rot = len(res["link_rotti"])

        tot_mantenuti += n_ok
        tot_rimossi   += n_rim
        tot_scaduti   += n_sca
        tot_rotti     += n_rot

        if res["ok"]:
            print(f"  OK -- {n_ok} raccomandazioni valide")
        else:
            totale_ok = False
            if n_rim: print(f"  RIMOSSI {n_rim} ID inesistenti")
            if n_sca: print(f"  RIMOSSI {n_sca} bandi scaduti")
            if n_rot: print(f"  RIMOSSI {n_rot} bandi con link rotto")
            print(f"  Rimaste valide: {n_ok}")
        print()

    print("=" * 60)
    print(f"  Mantenuti : {tot_mantenuti}")
    print(f"  Rimossi   : {tot_rimossi + tot_scaduti + tot_rotti}  "
          f"(inesistenti:{tot_rimossi} scaduti:{tot_scaduti} link-rotti:{tot_rotti})")
    if totale_ok:
        print("\n  OK -- Tutti i file sono validi.")
    else:
        print("\n  ATTENZIONE -- Alcuni file sono stati corretti.")
    print("=" * 60)

    return 0 if totale_ok else 1


if __name__ == "__main__":
    sys.exit(main())
