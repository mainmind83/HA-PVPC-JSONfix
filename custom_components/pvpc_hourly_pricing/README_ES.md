# PVPC Hourly Pricing — Corrección automática de festivos P3

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/HA-2024.6%2B-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 [English version](README.md)

Parche para la integración oficial `pvpc_hourly_pricing` de Home Assistant, que dejó de funcionar el 1 de enero de 2026 por un bug en la librería `aiopvpc`.

## ¿Qué problema resuelve?

La librería `aiopvpc` tiene los festivos nacionales de España **hardcodeados** en un diccionario Python que solo llega hasta 2025. Al entrar en 2026, el código lanza `KeyError: 2026` y la integración deja de funcionar.

### ¿Por qué este parche y no otro?

| Solución | Evita crash | Festivos correctos | Sin mantenimiento anual |
|----------|:-----------:|:------------------:|:----------------------:|
| `defaultdict(set)` (HA-PVPC-Updated) | ✅ | ❌ vacíos para 2026+ | ✅ pero datos erróneos |
| Bump a aiopvpc 4.3.1 (PR #167189) | ❌ sigue cubriendo solo hasta 2025 | ❌ | ❌ |
| ha-pvpc-next | ✅ | ✅ | ✅ (integración nueva completa) |
| **HA-PVPC-JSONfix v0.2.0** | ✅ | ✅ | ✅ cálculo automático |

Desde la v0.2.0, este parche **calcula los festivos P3 automáticamente** para cualquier año usando el algoritmo de Pascua gregoriano. Sin fichero JSON, sin descargas externas, sin actualizaciones anuales. Simplemente funciona.

---

## Cómo funciona

El parche reemplaza el diccionario hardcodeado de `aiopvpc` con un `_AutoHolidaysDict` — una subclase de `dict` en Python que, en lugar de lanzar `KeyError` para un año que falta, calcula los 10 festivos nacionales P3 al vuelo:

- **9 festivos con fecha fija** (iguales cada año)
- **1 festivo variable**: Viernes Santo, calculado a partir de la Pascua usando el [algoritmo gregoriano anónimo](https://en.wikipedia.org/wiki/Date_of_Easter#Anonymous_Gregorian_algorithm)

Opcionalmente, si existe `/config/pvpc_festivos_p3.json`, su contenido se usa como override manual (por ejemplo, para añadir festivos extra para pruebas o comparación).

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

### Paso 3 — Reiniciar Home Assistant

Ajustes → Sistema → Reiniciar, o:
```bash
ha core restart
```

> **Nota:** Desde la v0.2.0, copiar `pvpc_festivos_p3.json` **ya no es necesario**. Los festivos se calculan automáticamente. El fichero JSON solo se necesita si quieres sobreescribir fechas manualmente.

### Paso 4 — Verificar

Comprueba los logs en **Ajustes → Sistema → Registros**. Deberías ver:

```
INFO [...] PVPC festivos P3: años precargados [2021, 2022, 2023, 2024, 2025], años futuros se calcularán automáticamente (JSON override: no encontrado)
```

Cuando la integración consulte 2026 por primera vez:

```
INFO [...] Festivos P3 calculados automáticamente para 2026: ['2026-01-01', '2026-01-06', '2026-04-03', '2026-05-01', '2026-08-15', '2026-10-12', '2026-11-01', '2026-12-06', '2026-12-08', '2026-12-25']
```

---

## Base legal: ¿qué se considera P3?

La definición del periodo P3 (valle) viene de la **Circular 3/2020 de la CNMC** ([BOE-A-2020-1066](https://www.boe.es/buscar/doc.php?id=BOE-A-2020-1066)), que establece la metodología para el cálculo de los peajes de transporte y distribución de electricidad:

> *«Se consideran como horas del periodo 3 (valle) todas las horas de los sábados, domingos, el 6 de enero y los días festivos de ámbito nacional, definidos como tales en el calendario oficial del año correspondiente, **con exclusión tanto de los festivos sustituibles como de los que no tienen fecha fija**.»*

Esto significa:

### ✅ Siempre P3 (24h valle) — Festivos nacionales no sustituibles con fecha fija

| Festivo | Fecha | Base legal |
|---------|-------|------------|
| Año Nuevo | 1 de enero | No sustituible, fecha fija |
| Epifanía | 6 de enero | Sustituible pero mantenido por las 17 CCAA + mencionado explícitamente en la Circular CNMC |
| Día del Trabajo | 1 de mayo | No sustituible, fecha fija |
| Asunción | 15 de agosto | No sustituible, fecha fija |
| Fiesta Nacional | 12 de octubre | No sustituible, fecha fija |
| Todos los Santos | 1 de noviembre | No sustituible, fecha fija |
| Constitución | 6 de diciembre | No sustituible, fecha fija |
| Inmaculada | 8 de diciembre | No sustituible, fecha fija |
| Navidad | 25 de diciembre | No sustituible, fecha fija |

### ⚠️ Viernes Santo — Caso especial

El Viernes Santo es un **festivo nacional no sustituible**, pero **no tiene fecha fija** (depende de la Pascua). Según la lectura estricta de la Circular de la CNMC, debería quedar excluido del P3.

Sin embargo, en la práctica:
- La librería original `aiopvpc` lo incluye como P3
- La mayoría de distribuidoras eléctricas lo facturan como P3 (valle)
- Todos los parches de la comunidad (HA-PVPC-Updated, ha-pvpc-next) lo incluyen

**Este parche incluye el Viernes Santo como P3**, siguiendo la práctica habitual del sector y el comportamiento original de `aiopvpc`. Si algún día la regulación se aplica estrictamente, los usuarios pueden sobreescribirlo mediante el fichero JSON opcional.

### ❌ Nunca P3

- **Festivos autonómicos** (Comunidad Autónoma): aunque sea festivo en tu comunidad, la electricidad se factura a tarifas normales P1/P2/P3 de día laborable
- **Festivos locales** (municipales): igual que los autonómicos
- **Festivos nacionales sustituibles** que una CCAA haya reemplazado por otro

La tarifa PVPC se aplica a **nivel nacional**, no autonómico. Tu distribuidora no ajusta los periodos P3 según el calendario de tu comunidad autónoma.

---

## Herramienta auxiliar: update_festivos.py

Este repositorio incluye `update_festivos.py`, un script Python que parsea el CSV oficial de la web de la Seguridad Social ([seg-social.es](https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/)) y genera/actualiza el fichero JSON de festivos.

**Esta herramienta no es necesaria para que el parche funcione.** Se proporciona con fines de documentación y verificación — por ejemplo, para comparar los festivos calculados automáticamente con los datos oficiales del gobierno.

### Uso

1. Visita https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/
2. Descarga la exportación CSV (requiere sesión de navegador)
3. Ejecuta el script:

```bash
python3 update_festivos.py calendario.csv
```

El script:
- Extrae los festivos nacionales del CSV (`TIPO = Nacional`)
- Añade festivos fijos P3 que puedan faltar en el CSV (por ejemplo, Todos los Santos o Constitución, que pueden no aparecer como "Nacional" cuando caen en domingo y la CCAA los traslada)
- Actualiza o crea `/config/pvpc_festivos_p3.json`

### Formato del CSV (seg-social.es)

```csv
PROVINCIA,LOCALIDAD,FECHA,TIPO,DESCRIPCION
,,01-01-2026,Nacional,"Año Nuevo"
,,06-01-2026,Nacional,"Epifania del Señor"
,,03-04-2026,Nacional,"Viernes Santo"
...
```

> **Nota:** El endpoint de seg-social.es (`CalendarioServlet?exportacion=CSV&tipo=0`) requiere sesión de navegador (cookie JSESSIONID). Las llamadas directas con `curl` sin cookies devuelven respuestas vacías (HTTP 200, Content-Length: 0). El CSV debe descargarse manualmente desde la web.

---

## Opcional: fichero JSON de override

Si necesitas sobreescribir los festivos calculados automáticamente (por ejemplo, para pruebas o para añadir fechas específicas), crea `/config/pvpc_festivos_p3.json`:

```json
{
  "2026": [
    "2026-01-01", "2026-01-06", "2026-04-03", "2026-05-01",
    "2026-08-15", "2026-10-12", "2026-11-01", "2026-12-06",
    "2026-12-08", "2026-12-25"
  ]
}
```

Cuando el fichero JSON existe, sus fechas tienen prioridad sobre el cálculo automático para los años que contiene. Los años que no están en el JSON se siguen calculando automáticamente.

---

## Desinstalación

Cuando HA Core integre un fix definitivo:

```bash
rm -r /config/custom_components/pvpc_hourly_pricing
rm -f /config/pvpc_festivos_p3.json
```

Reinicia HA y la integración oficial volverá a funcionar.

---

## Contexto y referencias

- [Circular 3/2020 de la CNMC](https://www.boe.es/buscar/doc.php?id=BOE-A-2020-1066) — Definición legal de los periodos P3 y festivos
- [BOE — Calendario laboral 2026](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667) — Festivos nacionales oficiales para 2026
- [Issue #160084](https://github.com/home-assistant/core/issues/160084) — Primer reporte del bug
- [Issue #161231](https://github.com/home-assistant/core/issues/161231) — Confirmación con traceback
- [Issue #162550](https://github.com/home-assistant/core/issues/162550) — Petición de actualización
- [PR #167189](https://github.com/home-assistant/core/pull/167189) — Bump a aiopvpc 4.3.1 (no soluciona el problema — la v4.3.1 sigue cubriendo solo hasta 2025)

## Changelog

### v0.2.0
- **Cálculo automático de festivos** — sin fichero JSON ni datos externos
- Viernes Santo calculado con algoritmo de Pascua gregoriano (verificado 2021–2035)
- `_AutoHolidaysDict` reemplaza `defaultdict(set)` — calcula años faltantes al vuelo
- Fichero JSON ahora opcional (solo override manual)
- Añadido script auxiliar `update_festivos.py` para comparación con CSV
- Añadida documentación de referencia legal (Circular 3/2020 CNMC)

### v0.1.0
- Versión inicial con fichero JSON externo de festivos
- `defaultdict(set)` con merge de JSON para festivos P3 correctos

## Licencia

MIT — Misma licencia que la integración original y que `aiopvpc`.
