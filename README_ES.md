# PVPC Hourly Pricing — Parche con festivos P3 en JSON externo

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/HA-2024.6%2B-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 [English version](README.md)

Parche para la integración oficial `pvpc_hourly_pricing` de Home Assistant, que dejó de funcionar el 1 de enero de 2026 por un bug en la librería `aiopvpc`.

## ¿Qué problema resuelve?

La librería `aiopvpc` tiene los festivos nacionales de España **hardcodeados** en un diccionario Python que solo llega hasta 2025. Al entrar en 2026, el código lanza `KeyError: 2026` y la integración deja de funcionar.

### ¿Por qué este parche y no otro?

| Solución | Evita crash | Festivos correctos | Actualizable sin código |
|----------|:-----------:|:------------------:|:----------------------:|
| `defaultdict(set)` (HA-PVPC-Updated) | ✅ | ❌ vacíos para 2026+ | ❌ |
| ha-pvpc-next | ✅ | ✅ | ✅ (integración nueva completa) |
| **HA-PVPC-JSONfix** | ✅ | ✅ | ✅ (editar un fichero JSON) |

El parche `defaultdict(set)` evita el crash, pero al devolver un set vacío para 2026+, **días como el 1 de mayo o el 12 de octubre no se facturan como P3 (valle)** como deberían.

Este parche carga los festivos desde un fichero JSON editable (`/config/pvpc_festivos_p3.json`), con datos correctos de 2021 a 2027.

---

## Instalación

### Paso 1 — Copiar los ficheros de la integración oficial

Necesitas copiar la integración oficial a `custom_components`. Elige el método según tu instalación:

#### Método A — HA-OS / File Editor (sin SSH)

1. Usando **File Editor** o **Samba**, crea la carpeta:
   ```
   /config/custom_components/pvpc_hourly_pricing/
   ```

2. Descarga **todos los ficheros** de la integración oficial:
   https://github.com/home-assistant/core/tree/dev/homeassistant/components/pvpc_hourly_pricing

   Necesitas estos ficheros:
   - `__init__.py`
   - `config_flow.py`
   - `const.py`
   - `coordinator.py`
   - `helpers.py`
   - `manifest.json`
   - `sensor.py`
   - `strings.json`
   - Carpeta `translations/` (con todos los ficheros dentro)

3. Copia todos los ficheros descargados a `/config/custom_components/pvpc_hourly_pricing/`

#### Método B — SSH / Docker

Si tienes acceso SSH (por ejemplo con el add-on Advanced SSH & Web Terminal con Protection Mode desactivado):

```bash
mkdir -p /config/custom_components
docker cp homeassistant:/usr/src/homeassistant/homeassistant/components/pvpc_hourly_pricing \
  /config/custom_components/
```

### Paso 2 — Instalar el parche

#### Vía HACS (recomendado)

1. En Home Assistant, abre **HACS → Integraciones**
2. Menú ⋮ → **Repositorios personalizados**
3. Añade la URL: `https://github.com/mainmind83/HA-PVPC-JSONfix` — Categoría: **Integración**
4. Busca **PVPC Hourly Pricing — JSON Holidays Fix** e instala
5. Esto sobreescribe `__init__.py` y `manifest.json` con las versiones parcheadas

#### Manual

Descarga `__init__.py` y `manifest.json` de este repositorio y cópialos en `/config/custom_components/pvpc_hourly_pricing/`, sobreescribiendo los originales.

### Paso 3 — Copiar el fichero de festivos

Copia `pvpc_festivos_p3.json` a la raíz de tu configuración:

#### Vía File Editor:
El fichero está en `/config/custom_components/pvpc_hourly_pricing/pvpc_festivos_p3.json` — cópialo a `/config/pvpc_festivos_p3.json`

#### Vía SSH:
```bash
cp /config/custom_components/pvpc_hourly_pricing/pvpc_festivos_p3.json /config/
```

### Paso 4 — Reiniciar Home Assistant

Ajustes → Sistema → Reiniciar, o:
```bash
ha core restart
```

### Paso 5 — Verificar

Comprueba los logs en **Ajustes → Sistema → Registros**. Deberías ver:

```
INFO [...] Festivos P3 cargados desde /config/pvpc_festivos_p3.json: años [2021, 2022, 2023, 2024, 2025, 2026, 2027]
```

---

## Actualización anual

Edita `/config/pvpc_festivos_p3.json` y añade el nuevo año. De los 10 festivos nacionales P3, **9 son siempre las mismas fechas** — solo cambia el Viernes Santo:

| Festivo | Fecha | Nota |
|---------|-------|------|
| Año Nuevo | 1 de enero | Fija |
| Epifanía | 6 de enero | Fija |
| Viernes Santo | Variable | Cambia cada año |
| Día del Trabajo | 1 de mayo | Fija |
| Asunción | 15 de agosto | Fija |
| Fiesta Nacional | 12 de octubre | Fija |
| Todos los Santos | 1 de noviembre | Fija |
| Constitución | 6 de diciembre | Fija |
| Inmaculada | 8 de diciembre | Fija |
| Navidad | 25 de diciembre | Fija |

Cuando el BOE publique el calendario laboral (normalmente en octubre), solo tienes que añadir una entrada con la fecha del nuevo Viernes Santo.

---

## Desinstalación

Cuando HA Core integre un fix definitivo:

```bash
rm -r /config/custom_components/pvpc_hourly_pricing
rm /config/pvpc_festivos_p3.json
```

Reinicia HA y la integración oficial volverá a funcionar.

---

## Contexto

- [Issue #160084](https://github.com/home-assistant/core/issues/160084) — Primer reporte del bug
- [Issue #161231](https://github.com/home-assistant/core/issues/161231) — Confirmación
- [Issue #162550](https://github.com/home-assistant/core/issues/162550) — Petición de actualización
- [BOE — Festivos 2026](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667)

## Licencia

MIT — Misma licencia que la integración original y que `aiopvpc`.
