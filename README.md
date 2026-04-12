# PVPC Hourly Pricing — Parche con festivos P3 en JSON externo

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/HA-2024.6%2B-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇪🇸 [Versión en español](README_ES.md)

Patch for the official `pvpc_hourly_pricing` Home Assistant integration, which stopped working on January 1st 2026 due to a bug in the `aiopvpc` library.

## What problem does it solve?

The `aiopvpc` library has Spain's national holidays **hardcoded** in a Python dictionary that only covers up to 2025. On January 1st 2026, the code throws `KeyError: 2026` and the integration stops working entirely.

### Why this patch and not others?

| Solution | Prevents crash | Correct holidays | Updatable without code |
|----------|:-----------:|:------------------:|:----------------------:|
| `defaultdict(set)` (HA-PVPC-Updated) | ✅ | ❌ empty for 2026+ | ❌ |
| ha-pvpc-next | ✅ | ✅ | ✅ (full new integration) |
| **HA-PVPC-JSONfix** | ✅ | ✅ | ✅ (edit a JSON file) |

The `defaultdict(set)` patch prevents the crash, but returns empty holidays for 2026+, meaning **days like May 1st or October 12th are not billed as P3 (valley)** as they should be.

This patch loads holidays from an editable JSON file (`/config/pvpc_festivos_p3.json`), with correct data from 2021 to 2027 included.

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

### Step 3 — Copy the holidays file

Copy `pvpc_festivos_p3.json` to the root of your config:

#### Via File Editor:
The file is at `/config/custom_components/pvpc_hourly_pricing/pvpc_festivos_p3.json` — copy it to `/config/pvpc_festivos_p3.json`

#### Via SSH:
```bash
cp /config/custom_components/pvpc_hourly_pricing/pvpc_festivos_p3.json /config/
```

### Step 4 — Restart Home Assistant

Settings → System → Restart, or:
```bash
ha core restart
```

### Step 5 — Verify

Check the logs at **Settings → System → Logs**. You should see:

```
INFO [...] Festivos P3 cargados desde /config/pvpc_festivos_p3.json: años [2021, 2022, 2023, 2024, 2025, 2026, 2027]
```

---

## Yearly update

Just edit `/config/pvpc_festivos_p3.json` and add the new year. Out of the 10 national P3 holidays, **9 have fixed dates every year** — only Good Friday changes:

| Holiday | Date | Note |
|---------|------|------|
| New Year | January 1 | Fixed |
| Epiphany | January 6 | Fixed |
| Good Friday | Variable | Changes each year |
| Labour Day | May 1 | Fixed |
| Assumption | August 15 | Fixed |
| National Day | October 12 | Fixed |
| All Saints | November 1 | Fixed |
| Constitution | December 6 | Fixed |
| Immaculate | December 8 | Fixed |
| Christmas | December 25 | Fixed |

When the BOE (Spanish Official Gazette) publishes the labour calendar (usually in October), just add one entry with the new Good Friday date.

---

## Uninstall

When HA Core integrates a permanent fix:

```bash
rm -r /config/custom_components/pvpc_hourly_pricing
rm /config/pvpc_festivos_p3.json
```

Restart HA and the official integration will take over again.

---

## Context

- [Issue #160084](https://github.com/home-assistant/core/issues/160084) — Original bug report
- [Issue #161231](https://github.com/home-assistant/core/issues/161231) — Confirmation
- [Issue #162550](https://github.com/home-assistant/core/issues/162550) — Update request
- [BOE — 2026 holidays](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667)

## License

MIT — Same license as the original integration and `aiopvpc`.
