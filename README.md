# 📡 BandiRadar

Sistema di monitoraggio bandi, incentivi e agevolazioni
**Fondi regionali Emilia-Romagna, nazionali ed europei**

> Costo operativo: **€ 0** — Tutto gratuito, tutto automatico.

---

## Struttura del progetto

```
BandiRadar/
├── index.html                          ← Dashboard web (apri nel browser)
├── data/
│   ├── bandi.csv                       ← Bandi attivi (aggiornato ogni notte)
│   ├── archivio.csv                    ← Bandi scaduti
│   └── last_sync.txt                   ← Data ultimo aggiornamento
├── .github/workflows/
│   ├── sync-sheets.yml                 ← Sync notturno Google Sheets → CSV
│   └── weekly-digest.yml              ← Email digest ogni lunedì mattina
├── scripts/
│   ├── monitor_eu.py                   ← Monitoraggio EU Funding Portal API
│   └── monitor_rss.py                  ← Monitoraggio RSS fonti nazionali/ER
└── README.md
```

---

## Setup completo (una tantum — circa 2 ore)

### FASE 1 — Google Sheet

1. Apri Google Drive e crea un nuovo Foglio Google chiamato **BandiRadar**
2. Rinomina il primo foglio in **Bandi** e crea le colonne nell'ordine esatto:

   ```
   ID | Nome bando | Ente erogatore | Livello | Categoria | Categoria principale |
   Beneficiari | Tipo agevolazione | Regime aiuto | Ambito geografico |
   Dettaglio geografico | ATECO ammessi | Cumulabilità | Note cumulabilità |
   Dotazione totale | Importo max beneficiario | Percentuale contributo |
   Data apertura | Scadenza | Tipo scadenza | Stato | Priorità | Link ufficiale |
   Data inserimento | Inserito da | File CSV
   ```

3. Copia i dati dal file `data/bandi.csv` come punto di partenza
4. Aggiungi un secondo foglio chiamato **Scartati** con le colonne:
   `Data controllo | Titolo/fonte | Link | Motivo scarto | Verificato da`
5. Aggiungi un terzo foglio chiamato **Note interne** con le colonne:
   `ID bando | Clienti interessati | Stato interno | Note libere`
6. **Condividi il foglio "Bandi" pubblicamente** (solo lettura) cliccando
   su "Condividi" → "Chiunque abbia il link" → "Visualizzatore"
7. Copia l'ID del foglio dall'URL:
   `https://docs.google.com/spreadsheets/d/`**[QUESTO-È-LO-SHEET-ID]**`/edit`

### FASE 2 — GitHub Repository

1. Vai su [github.com](https://github.com) e crea un account (gratuito)
2. Crea un nuovo repository pubblico chiamato `bandiradar`
   - ✅ Pubblico (necessario per GitHub Pages gratuito)
   - ✅ Aggiungi README
3. Carica tutti i file di questo progetto nel repository:
   - Puoi farlo trascinando i file nell'interfaccia web di GitHub
   - Oppure con Git da terminale: `git clone`, copia i file, `git push`

### FASE 3 — GitHub Pages (hosting dashboard)

1. Nel repository, vai su **Settings** → **Pages**
2. In "Source" seleziona **Deploy from a branch**
3. Branch: **main**, cartella: **/ (root)**
4. Clicca **Save**
5. Dopo 1-2 minuti la dashboard sarà online all'indirizzo:
   `https://[tuo-username].github.io/bandiradar/`

Puoi condividere questo URL con tutto il team. Si aggiorna automaticamente.

### FASE 4 — Secrets GitHub Actions

1. Nel repository, vai su **Settings** → **Secrets and variables** → **Actions**
2. Aggiungi i seguenti secrets (cliccando "New repository secret"):

| Secret | Valore | Descrizione |
|--------|--------|-------------|
| `SHEET_ID` | `1BxiMVs0XRA...` | ID del tuo Google Sheet (dalla URL) |
| `SMTP_USER` | `bandiradar@gmail.com` | Email Gmail mittente |
| `SMTP_PASS` | `xxxx xxxx xxxx xxxx` | App Password Gmail (vedi sotto) |
| `DIGEST_EMAILS` | `mario@azienda.it,lucia@azienda.it` | Destinatari email digest |
| `NOTIFY_EMAIL` | `mario@azienda.it` | Destinatario alert errori |

**Come ottenere App Password Gmail:**
1. Vai su [myaccount.google.com](https://myaccount.google.com)
2. Sicurezza → Verifica in 2 passaggi → App password
3. Seleziona "Altra app (nome personalizzato)" → scrivi "BandiRadar" → Genera
4. Copia la password a 16 caratteri generata

### FASE 5 — Test e dati pilota

1. Verifica che la dashboard si apra correttamente all'URL GitHub Pages
2. Inserisci 15-20 bandi pilota nel Google Sheet
3. Testa il sync manualmente: vai su **Actions** → **Sync Notturno** → **Run workflow**
4. Testa l'email digest: vai su **Actions** → **Digest Settimanale Email** → **Run workflow**
5. Controlla che l'email arrivi correttamente

---

## Uso quotidiano

### Lunedì mattina (10-15 min)
```bash
# Esegui gli script di monitoraggio
python scripts/monitor_eu.py
python scripts/monitor_rss.py
```
Per ogni bando trovato: verifica il link, inserisci nel Sheet se reale,
annota nel foglio Scartati se falso positivo.

### Durante la settimana (5-10 min)
Controlla manualmente le fonti senza RSS (Incentivi.gov, Regione ER, ecc.)

### Venerdì (5-10 min)
- Aggiorna stati "In arrivo" → "Aperto" se pubblicati
- Controlla eventuali proroghe annunciate
- Aggiorna eventuali bandi sospesi

---

## Come inserire un nuovo bando nel Google Sheet

| Campo | Valore da inserire |
|-------|-------------------|
| ID | Formato: `ER-2026-042` (livello-anno-numero) |
| Livello | `Europeo` oppure `Nazionale` oppure `Regionale ER` |
| Tipo scadenza | `Data fissa` / `Sportello (fino a esaurimento fondi)` / `Misura strutturale` / `Anno fiscale` |
| Stato | `Aperto` / `In arrivo` / `Prorogato` / `Sospeso` |
| File CSV | `Attivo` (bandi correnti) oppure `Archivio` (bandi scaduti) |
| Priorità | `Alta` / `Media` / `Bassa` |
| Date | Formato obbligatorio: `AAAA-MM-GG` (es. `2026-06-30`) |

---

## Manutenzione

Il sistema è quasi completamente autonomo. Gli unici interventi manuali sono:
- **Inserimento nuovi bandi** nel Google Sheet (settimanale, ~30-60 min)
- **Aggiornamento stati** bandi esistenti (settimanale, ~10 min)
- **Check GitHub Actions** se arrivano email di errore (raro, ~15 min)

Se cambia l'URL di export del Google Sheet, aggiorna il workflow `sync-sheets.yml`.

---

## Costi

| Voce | Costo |
|------|-------|
| Google Workspace (Sheets) | € 0 — già in uso |
| GitHub repository pubblico | € 0 |
| GitHub Pages hosting | € 0 |
| GitHub Actions (2000 min/mese free) | € 0 |
| Gmail SMTP | € 0 |
| **Totale annuo** | **€ 0** |

---

## Troubleshooting

**La dashboard non si aggiorna dopo il push**
→ GitHub Pages può impiegare fino a 5 minuti. Svuota la cache del browser (Ctrl+Shift+R).

**Il sync notturno fallisce**
→ Controlla che il Google Sheet sia condiviso pubblicamente e che SHEET_ID sia corretto.

**Le email non arrivano**
→ Verifica che SMTP_PASS sia l'App Password (non la password Gmail normale).
→ Controlla che la verifica in 2 passaggi sia attiva sull'account Gmail.

**Duplicati nel CSV**
→ Riceverai un'email di alert. Apri il Google Sheet, cerca il duplicato con Ctrl+F e rimuovi la riga extra.
