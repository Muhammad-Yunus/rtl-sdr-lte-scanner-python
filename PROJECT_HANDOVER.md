# PROJECT HANDOVER — LTE Cell Scanner on Raspberry Pi

> **Tanggal Handover**: 2026-01-02
> **Author**: Yunus (via AI assistant)
> **Target Hardware**: Raspberry Pi (ARM64) + RTL-SDR (RTL2838, R820T/R820T2 tuner)
> **Target OS**: Raspberry Pi OS (Debian-based, likely Bullseye/Buster)

---

## Apa yang Sudah Dibuat

Project ini adalah **wrapper Python** untuk srsRAN_4G yang dirancang dengan arsitektur clean architecture (Domain-Driven Design). Bagian Python sudah **100% selesai secara arsitektural** — semua modul, service layer, CLI, config, formatter, exporter, dan tests sudah ditulis dan lulus di Windows.

Yang **belum selesai** adalah **integrasi nyata dengan RTL-SDR** karena membutuhkan hardware Linux untuk men-build dan menjalankan `lte_cell_search` binary dari srsRAN_4G.

### Struktur Project

```
rtl-sdr-lte-scanner-python/
├── pyproject.toml              # Project config (pydantic, typer, toml)
├── configs/
│   └── config.toml             # Runtime config: device index, freq, bw, timeout, binary path
├── data/
│   └── operators.json          # MCC/MNC → operator/country lookup table
├── src/
│   ├── domain/
│   │   ├── models.py           # LTECell, OperatorEntry — domain model
│   │   ├── enums.py            # Band, BandwidthMHz, OutputFormat, ScanStatus
│   │   └── exceptions.py       # LteScannerError + subtypes (SdrNotFoundError, ParseError, dll)
│   ├── services/
│   │   ├── srsran_runner.py    # Subprocess wrapper — launches lte_cell_search binary
│   │   ├── cell_parser.py      # (TODO) — NOT YET IMPLEMENTED ⚠️
│   │   ├── operator_resolver.py # MCC/MNC → operator/country enrichment
│   │   ├── formatter.py         # Render LTECell → table/JSON/CSV/YAML
│   │   └── exporter.py          # Write cells to .json / .csv files
│   ├── application/
│   │   └── scanner.py          # ScanService — orchestrates runner + parser + resolver
│   ├── repository/
│   │   └── operator_db.py      # Loads operators.json into dict for lookup
│   ├── infrastructure/
│   │   ├── config.py           # pydantic model loader from config.toml
│   │   ├── logger.py           # Python logging setup
│   │   └── filesystem.py       # File/dir helpers for export
│   ├── cli/
│   │   └── main.py             # Typer CLI: scan, export, version commands
│   └── utils/
│       ├── frequency.py        # EARFCN ↔ MHz converter
│       └── validation.py       # Input validators
├── tests/                      # All passing on Windows ✓
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_exceptions.py
│   ├── test_formatter.py
│   ├── test_exporter.py
│   ├── test_scanner.py
│   ├── test_srsran_runner.py
│   └── ...
└── PROJECT_HANDOVER.md
```

---

## Ringkasan Arsitektur

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│   CLI (Typer)   │────▶│ Scanner      │────▶│ srsRAN Runner │
│  scan / export  │     │  Service     │     │  (subprocess) │
└─────────────────┘     └──────┬───────┘     └───────┬───────┘
                               │                      │
                    ┌──────────▼───────┐      ┌───────▼────��───┐
                    │  Cell Parser     │◀─────│ lte_cell_search│
                    │  (TODO ⚠️)        │      │  binary        │
                    └──────────┬───────┘      └────────────────┘
                               │
                    ┌──────────▼───────┐     ┌───────────────┐
                    │  Operator        │     │  Formatter     │
                    │  Resolver        │     │  (table/json/  │
                    │  (MCC/MNC→name)  │     │  csv/yaml)     │
                    └──────────────────┘     └───────────────┘
```

---

## Yang Perlu Dilakukan di Raspberry Pi

### Langkah 1: Clone Repo

```bash
cd /home/pi
git clone https://github.com/Muhammad-Yunus/rtl-sdr-lte-scanner-python.git
cd rtl-sdr-lte-scanner-python
```

### Langkah 2: Install Dependencies Python

```bash
# srsRAN_4G sudah terinstall di /home/pi/srsRAN_4G/
# binary ada di: /home/pi/srsRAN_4G/build/lib/examples/cell_search
# RTL-SDR sudah terdeteksi (verifikasi: lsusb | grep rtl)

sudo apt install python3-pip python3-venv
python3 -m venv ~/sdr-env
source ~/sdr-env/bin/activate

# Install dari pyproject.toml (sesuaikan dengan dependencies di pyproject.toml)
pip install pydantic typer tomli>=1.1.0

# Jika pyproject.toml ada dependencies lain:
pip install pyyaml  # untuk YAML output format
pip install rich    # opsional, untuk table rendering
```

### Langkah 3: Verifikasi RTL-SDR & srsRAN Binary

```bash
# Verifikasi RTL-SDR terdeteksi
lsusb | grep -i rtl

# Verifikasi SoapySDR bisa detect device
SoapySDRUtil --find

# Verifikasi cell_search binary
ls -la /home/pi/srsRAN_4G/build/lib/examples/cell_search

# Test singkat (akan menghasilkan output cell search)
/home/pi/srsRAN_4G/build/lib/examples/cell_search -b 8 -g 42
```

### Langkah 4: Konfigurasi

Edit `configs/config.toml` — set `binary_path` ke path absolut srsRAN cell_search:

```toml
[srsran]
binary_path = "/home/pi/srsRAN_4G/build/lib/examples/cell_search"

[device]
index = 0

[scan]
default_frequency_mhz = 869.5
timeout_seconds = 30

[output]
format = "table"
```

### Langkah 5: Implementasi CellParser (TUGAS UTAMA ⚠️)

Ini adalah bagian paling kritis yang **belum ada**. File yang perlu dibuat:

**`src/services/cell_parser.py`**

File ini bertanggung jawab untuk **mem-parse output teks** dari `lte_cell_search` binary menjadi list of `LTECell` domain objects.

#### Format Output yang Diharapkan dari `lte_cell_search`

Dari dokumentasi `/home/pi/srsRAN_4G/HOW_TO_USE_SRSRAN.md`, output seperti ini:

```
Found CELL ID 2. 50 PRB, 1 ports
Found CELL ID 243. 50 PRB, 2 ports
Found CELL ID 416. 50 PRB, 2 ports
Found CELL ID 0. 75 PRB, 2 ports
Found 4 cells
Found CELL 930.0 MHz, EARFCN=3500, PHYID=2, 50 PRB, 1 ports, PSS power=-21.3 dBm
Found CELL 930.1 MHz, EARFCN=3501, PHYID=243, 50 PRB, 2 ports, PSS power=-20.3 dBm
Found CELL 930.1 MHz, EARFCN=3501, PHYID=416, 50 PRB, 2 ports, PSS power=-18.5 dBm
Found CELL 945.5 MHz, EARFCN=3655, PHYID=0, 75 PRB, 2 ports, PSS power=-26.6 dBm
```

#### Spec `cell_parser.py`

```python
"""Parser untuk output teks dari lte_cell_search binary.

Harapan: mengubah raw stdout menjadi list[LTECell] berdasarkan
format output: "Found CELL {freq} MHz, EARFCN={earfcn}, PHYID={pci}, {prb} PRB, {ports} ports, PSS power={power} dBm"

Perlu parsing regex untuk setiap baris yang diawali "Found CELL".
```

**Catatan penting:**
- `PRB` → konversi ke `BandwidthMHz`: 6=1.4, 15=3, 25=5, 50=10, 75=15, 100=20
- `PHYID` → `pci` (Physical Cell ID)
- `PSS power` → bisa jadi `rsrp` (Reference Signal Received Power)
- `ports` → informasi antenna (1 = SISO, 2 = MIMO) — tidak langsung masuk LTECell
- Frequency → `frequency_mhz`
- EARFCN → `earfcn`

---

### Langkah 6: Jalankan

```bash
source ~/sdr-env/bin/activate

# Test CLI scan
cd /home/pi/rtl-sdr-lte-scanner-python
python -m lte_scan.cli scan --config configs/config.toml

# Test scan band 5
python -m lte_scan.cli scan --config configs/config.toml --band 5

# Test export
python -m lte_scan.cli export --config configs/config.toml exports/result.json
```

---

## Catatan Penting

### srsRAN_4G di Pi

- **Binary path**: `/home/pi/srsRAN_4G/build/lib/examples/cell_search`
- **Build location**: `/home/pi/srsRAN_4G/build/`
- **Source**: `/home/pi/srsRAN_4G/`
- **Dokumentasi lengkap**: `/home/pi/srsRAN_4G/HOW_TO_USE_SRSRAN.md`

### Perilaku `lte_cell_search`

- Hanya menerima `-b <band>` (band LTE: 3, 5, 8, dll)
- `-g <gain>`: optimal 40-49 dB untuk RTL-SDR
- `-s <earfcn_start>` dan `-e <earfcn_end>`: membatasi range EARFCN
- `-n <frames>`: jumlah frames per EARFCN (default 100, lebih banyak = lebih akurat)
- Scan satu band penuh bisa 5-15 menit di Pi

### Band yang Didukung RTL-SDR

| Band | Status | Keterangan |
|------|--------|------------|
| **Band 8** (925-960 MHz) | ✅ Recommended | Paling stabil untuk R820T |
| **Band 5** (869-894 MHz) | ✅ Bagus | Band yang dipilih user |
| **Band 3** (1805-1880 MHz) | ⚠️ Berisiko | Sering PLL gagal lock |
| **Band 1, 40** | ❌ Tidak support | Terlalu tinggi untuk R820T |

### Batasan Hardware

- RTL-SDR hanya RX (receive only), tidak bisa TX
- Max sample rate ~3.2 MHz
- Tidak bisa decode PDSCH, hanya cell search
- srsue/srsenb/tTDD tidak bisa digunakan (butuh TX)

---

## Checklist untuk Melanjutkan

- [ ] Clone repo ke Pi (`git clone`)
- [ ] Setup virtualenv & install dependencies (`pip install ...`)
- [ ] Implementasikan `src/services/cell_parser.py` — parse output `lte_cell_search`
- [ ] Tulis unit tests untuk `cell_parser.py` (mock stdout dari binary)
- [ ] Verifikasi `lte_cell_search` binary benar di `cell_search.py` runner
- [ ] Test CLI `scan` command dengan RTL-SDR
- [ ] Test CLI `export` command (JSON/CSV)
- [ ] Test operator resolver (MCC/MNC lookup)
- [ ] Update `config.toml` di Pi dengan binary path yang benar
- [ ] Commit perubahan ke repository

---

## Ringkasan Dependencies

| Package | Fungsi | Status |
|---------|--------|--------|
| **srsRAN_4G** | Cell search binary (`lte_cell_search`) | ✅ Sudah terinstall di Pi |
| **RTL-SDR (Zadig)** | Driver USB untuk RTL dongle | ✅ Sudah terpasang |
| **SoapySDR + rtlsdr** | RF abstraction layer untuk srsRAN | ✅ Sudah terinstall di Pi |
| **Python 3.12+** | Runtime untuk project | ⚠️ Perlu install di Pi |
| **Pydantic** | Config validation + models | ⚠️ Perlu pip install |
| **Typer** | CLI framework | ⚠️ Perlu pip install |
| **tomli/tomllib** | TOML config parsing | ⚠️ Perlu pip install |

---

## Transfer Workflow

1. **Push semua perubahan dari Windows** ke GitHub (sudah include semua modul Python yang sudah dibuat)
2. **Clone di Raspberry Pi**
3. **Implementasikan `cell_parser.py`** sesuai format output dari `lte_cell_search`
4. **Test & commit** perubahan di Pi
5. **Pull balik** hasilnya ke repository utama
