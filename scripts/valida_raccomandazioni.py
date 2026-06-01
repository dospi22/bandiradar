"""
valida_raccomandazioni.py
=========================
Legge bandi.csv e raccomandazioni.json, verifica che ogni ID raccomandato
esista nel CSV, rimuove quelli inesistenti e salva il JSON pulito.

Uso:
    python scripts/valida_raccomandazioni.py

Oppure importato da altri script:
    from scripts.valida_raccomandazioni import valida
"""

import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CSV_PATH = BASE_DIR / "data" / "bandi.csv"
JSON_PATH = BASE_DIR / "data" / "raccomandazioni.json"


def carica_id_validi(csv_path: Path) -> set:
    """Legge bandi.csv e restituisce l'insieme degli ID presenti."""
    id_validi = set()
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bid = row.get("ID", "").strip()
            if bid:
                id_validi.add(bid)
    return id_validi


def valida(
    json_path: Path = JSON_PATH,
    csv_path: Path = CSV_PATH,
    salva: bool = True,
) -> dict:
    """
    Valida raccomandazioni.json contro bandi.csv.

    Restituisce un dict con:
        ok        : bool — True se nessun ID è stato rimosso
        rimossi   : list — ID rimossi perché inesistenti nel CSV
        mantenuti : list — ID validi rimasti
        dati      : dict — contenuto JSON aggiornato (se salva=True, già scritto su disco)
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV non trovato: {csv_path}")
    if not json_path.exists():
        raise FileNotFoundError(f"JSON non trovato: {json_path}")

    id_validi = carica_id_validi(csv_path)

    with open(json_path, encoding="utf-8") as f:
        dati = json.load(f)

    rimossi_totali = []
    mantenuti_totali = []

    for azienda in dati.get("aziende", []):
        racc_originali = azienda.get("raccomandazioni", [])
        racc_valide = []
        for r in racc_originali:
            bid = r.get("id", "")
            if bid in id_validi:
                racc_valide.append(r)
                mantenuti_totali.append(bid)
            else:
                rimossi_totali.append(bid)
                print(
                    f"  [RIMOSSO] ID '{bid}' non trovato in bandi.csv "
                    f"(azienda: {azienda.get('idAzienda', '?')})"
                )
        azienda["raccomandazioni"] = racc_valide

    if salva and rimossi_totali:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        print(f"\n  File aggiornato: {json_path}")

    return {
        "ok": len(rimossi_totali) == 0,
        "rimossi": rimossi_totali,
        "mantenuti": mantenuti_totali,
        "dati": dati,
    }


def main():
    print("=" * 55)
    print("  BandiRadar — Validazione raccomandazioni.json")
    print("=" * 55)

    try:
        risultato = valida()
    except FileNotFoundError as e:
        print(f"\nERRORE: {e}")
        sys.exit(1)

    n_rimossi = len(risultato["rimossi"])
    n_ok = len(risultato["mantenuti"])

    print(f"\n  ID validi mantenuti : {n_ok}")
    print(f"  ID rimossi (falsi)  : {n_rimossi}")

    if risultato["ok"]:
        print("\n  OK — Nessun ID inesistente trovato.")
    else:
        print(f"\n  ATTENZIONE — Rimossi {n_rimossi} ID non presenti nel CSV:")
        for bid in risultato["rimossi"]:
            print(f"    - {bid}")
        print("\n  raccomandazioni.json aggiornato e salvato.")

    print("=" * 55)
    return 0 if risultato["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
