# PVPC Hourly Pricing — Automatic P3 Holidays Fix

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/HA-2024.6%2B-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇪🇸 [Versión en español](README_ES.md)

Patch for the official `pvpc_hourly_pricing` Home Assistant integration, which stopped working on January 1st 2026 due to a bug in the `aiopvpc` library.

## What problem does it solve?

The `aiopvpc` library has Spain's national holidays **hardcoded** in a Python dictionary that only covers up to 2025. On January 1st 2026, the code throws `KeyError: 2026` and the integration stops working entirely.

### Why this patch and not others?

| Solution | Prevents crash | Correct holidays | No yearly maintenance |
|----------|:-----------:|:------------------:|:----------------------:|
| `defaultdict(set)` (HA-PVPC-Updated) | ✅ | ❌ empty for 2026+ | ✅ but wrong data |
| Bump to aiopvpc 4.3.1 (PR #167189) | ❌ still covers up to 2025 only | ❌ | ❌ |
| ha-pvpc-next | ✅ | ✅ | ✅ (full new integration) |
| **HA-PVPC-JSONfix v0.2.0** | ✅ | ✅ | ✅ automatic calculation |

Since v0.2.0, this patch **calculates P3 holidays automatically** for any year using the Gregorian Easter algorithm. No JSON file needed, no external downloads, no annual updates. It just works.

---

## How it works

The patch replaces `aiopvpc`'s hardcoded holiday dictionary with an `_AutoHolidaysDict` — a Python `dict` subclass that, instead of raising `KeyError` for a missing year, calculates the 10 national P3 holidays on-the-fly:

- **9 fixed-date holidays** (same every year)
- **1 variable holiday**: Good Friday, calculated from Easter using the [Anonymous Gregorian algorithm](https://en.wikipedia.org/wiki/Date_of_Easter#Anonymous_Gregorian_algorithm)

Optionally, if `/config/pvpc_festivos_p3.json` exists, its contents are used as a manual override (e.g., to add extra holidays for testing or comparison).

---

## Installation

### Step 1 — Copy the official integration files

You need to copy the official integration into `custom_components` first. Choose the method that matches your setup:

#### Method A — HA-OS / File Editor (no SSH needed)

1. Using **File Editor** or **Samba**, create the folder:
   ```
   /config/custom_components/pvpc_hourly_pricing/
   ```

2. Download **all files** from the official integration:
   https://github.com/home-assistant/core/tree/dev/homeassistant/components/pvpc_hourly_pricing

   You need these files:
   - `__init__.py`
   - `config_flow.py`
   - `const.py`
   - `coordinator.py`
   - `helpers.py`
   - `manifest.json`
   - `sensor.py`
   - `strings.json`
   - `translations/` folder (with all files inside)

3. Copy all downloaded files into `/config/custom_components/pvpc_hourly_pricing/`

#### Method B — SSH / Docker

If you have SSH access (e.g. via Advanced SSH & Web Terminal add-on with Protection Mode disabled):

```bash
mkdir -p /config/custom_components
docker cp homeassistant:/usr/src/homeassistant/homeassistant/components/pvpc_hourly_pricing \
  /config/custom_components/
```

### Step 2 — Install the patch

#### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**
2. Menu ⋮ → **Custom repositories**
3. Add URL: `https://github.com/mainmind83/HA-PVPC-JSONfix` — Category: **Integration**
4. Search for **PVPC Hourly Pricing — JSON Holidays Fix** and install
5. This overwrites `__init__.py` and `manifest.json` with the patched versions

#### Manual

Download `__init__.py` and `manifest.json` from this repo and copy them into `/config/custom_components/pvpc_hourly_pricing/`, overwriting the originals.

### Step 3 — Restart Home Assistant

Settings → System → Restart, or:
```bash
ha core restart
```

> **Note:** Since v0.2.0, copying `pvpc_festivos_p3.json` is **no longer required**. Holidays are calculated automatically. The JSON file is only needed if you want to manually override specific dates.

### Step 4 — Verify

Check the logs at **Settings → System → Logs**. You should see:

```
INFO [...] PVPC festivos P3: años precargados [2021, 2022, 2023, 2024, 2025], años futuros se calcularán automáticamente (JSON override: no encontrado)
```

When the integration queries 2026 for the first time:

```
INFO [...] Festivos P3 calculados automáticamente para 2026: ['2026-01-01', '2026-01-06', '2026-04-03', '2026-05-01', '2026-08-15', '2026-10-12', '2026-11-01', '2026-12-06', '2026-12-08', '2026-12-25']
```

---

## Legal basis: what counts as P3?

The P3 (valley) period definition comes from **CNMC Circular 3/2020** ([BOE-A-2020-1066](https://www.boe.es/buscar/doc.php?id=BOE-A-2020-1066)), which establishes the methodology for electricity transport and distribution tolls:

> *«Se consideran como horas del periodo 3 (valle) todas las horas de los sábados, domingos, el 6 de enero y los días festivos de ámbito nacional, definidos como tales en el calendario oficial del año correspondiente, **con exclusión tanto de los festivos sustituibles como de los que no tienen fecha fija**.»*

This means:

### ✅ Always P3 (24h valley) — National non-substitutable holidays with fixed date

| Holiday | Date | Legal basis |
|---------|------|-------------|
| New Year | January 1 | Non-substitutable, fixed |
| Epiphany | January 6 | Substitutable but kept by all 17 CCAA + explicitly mentioned in CNMC Circular |
| Labour Day | May 1 | Non-substitutable, fixed |
| Assumption | August 15 | Non-substitutable, fixed |
| National Day | October 12 | Non-substitutable, fixed |
| All Saints | November 1 | Non-substitutable, fixed |
| Constitution Day | December 6 | Non-substitutable, fixed |
| Immaculate Conception | December 8 | Non-substitutable, fixed |
| Christmas | December 25 | Non-substitutable, fixed |

### ⚠️ Good Friday — Special case

Good Friday is a **national non-substitutable holiday**, but it **does not have a fixed date** (it depends on Easter). According to the strict reading of the CNMC Circular, it should be excluded from P3.

However, in practice:
- The original `aiopvpc` library includes it as P3
- Most electricity distributors bill it as P3 (valley)
- All community workarounds (HA-PVPC-Updated, ha-pvpc-next) include it

**This patch includes Good Friday as P3**, matching the established industry practice and the original `aiopvpc` behavior. If the regulation is ever enforced strictly, users can override this via the optional JSON file.

### ❌ Never P3

- **Regional holidays** (Comunidad Autónoma): even if it's a holiday in your region, electricity is billed at normal P1/P2/P3 weekday rates
- **Local holidays** (municipal): same as above
- **Substitutable national holidays** that a CCAA has replaced with a regional one

The PVPC tariff is applied **nationally**, not regionally. Your distributor does not adjust P3 periods based on your autonomous community's calendar.

---

## Auxiliary tool: update_festivos.py

This repository includes `update_festivos.py`, a Python script that can parse the official CSV from Spain's Social Security website ([seg-social.es](https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/)) and generate/update the JSON holidays file.

**This tool is not required for the patch to work.** It is provided for documentation and verification purposes — for example, to compare the automatically calculated holidays against the official government data.

### Usage

1. Visit https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/
2. Download the CSV export (requires browser session — the endpoint needs cookies)
3. Run the script:

```bash
python3 update_festivos.py calendario.csv
```

The script will:
- Extract national holidays from the CSV (`TIPO = Nacional`)
- Add any fixed P3 holidays missing from the CSV (e.g., All Saints or Constitution Day, which may not appear as "Nacional" when they fall on Sunday and are moved by the CCAA)
- Update or create `/config/pvpc_festivos_p3.json`

### CSV format (seg-social.es)

```csv
PROVINCIA,LOCALIDAD,FECHA,TIPO,DESCRIPCION
,,01-01-2026,Nacional,"Año Nuevo"
,,06-01-2026,Nacional,"Epifania del Señor"
,,03-04-2026,Nacional,"Viernes Santo"
...
```

> **Note:** The seg-social.es endpoint (`CalendarioServlet?exportacion=CSV&tipo=0`) requires a browser session (JSESSIONID cookie). Direct `curl` calls without cookies return empty responses (HTTP 200, Content-Length: 0). The CSV must be downloaded manually through the web interface.

---

## Optional: JSON override file

If you need to override the automatically calculated holidays (e.g., for testing or to add specific dates), create `/config/pvpc_festivos_p3.json`:

```json
{
  "2026": [
    "2026-01-01", "2026-01-06", "2026-04-03", "2026-05-01",
    "2026-08-15", "2026-10-12", "2026-11-01", "2026-12-06",
    "2026-12-08", "2026-12-25"
  ]
}
```

When the JSON file exists, its dates take priority over the automatic calculation for the years it covers. Years not in the JSON are still calculated automatically.

---

## Uninstall

When HA Core integrates a permanent fix:

```bash
rm -r /config/custom_components/pvpc_hourly_pricing
rm -f /config/pvpc_festivos_p3.json
```

Restart HA and the official integration will take over again.

---

## Context and references

- [CNMC Circular 3/2020](https://www.boe.es/buscar/doc.php?id=BOE-A-2020-1066) — Legal definition of P3 periods and holidays
- [BOE — 2026 labour calendar](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667) — Official national holidays for 2026
- [Issue #160084](https://github.com/home-assistant/core/issues/160084) — Original bug report
- [Issue #161231](https://github.com/home-assistant/core/issues/161231) — Confirmation with traceback
- [Issue #162550](https://github.com/home-assistant/core/issues/162550) — Update request
- [PR #167189](https://github.com/home-assistant/core/pull/167189) — Bump to aiopvpc 4.3.1 (does not fix the issue — v4.3.1 still only covers up to 2025)

## Changelog

### v0.2.0
- **Automatic holiday calculation** — no JSON file or external data needed
- Good Friday calculated via Gregorian Easter algorithm (verified 2021–2035)
- `_AutoHolidaysDict` replaces `defaultdict(set)` — calculates missing years on-the-fly
- JSON file now optional (manual override only)
- Added `update_festivos.py` auxiliary script for CSV comparison
- Added legal reference documentation (CNMC Circular 3/2020)

### v0.1.0
- Initial release with external JSON holidays file
- `defaultdict(set)` with JSON merge for correct P3 holidays

## License

MIT — Same license as the original integration and `aiopvpc`.
