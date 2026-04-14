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
| **HA-PVPC-JSONfix v0.3.0** | ✅ | ✅ | ✅ cálculo automático |

Desde la v0.2.0, este parche **calcula los festivos P3 automáticamente** para cualquier año. Desde la v0.3.0, el cálculo está **alineado con la regulación de la CNMC y verificado con datos reales de facturación** de distribuidoras españolas.

---

## Cómo funciona

El parche reemplaza el diccionario hardcodeado de `aiopvpc` con un `_AutoHolidaysDict` — una subclase de `dict` en Python que, en lugar de lanzar `KeyError` para un año que falta, calcula los festivos P3 al vuelo:

- **9 festivos nacionales con fecha fija**, comprobados contra día de la semana (los que caen en fin de semana se excluyen — ya son P3 como sábado/domingo)
- **Viernes Santo excluido** — no tiene fecha fija y no es P3 según la regulación de la CNMC (confirmado con datos reales de facturación de e-distribución)
- **Lookahead del año siguiente** — se incluyen el 1 y 6 de enero del año siguiente para cubrir la transición de año

Opcionalmente, si existe `/config/pvpc_festivos_p3.json`, su contenido se usa como override manual (por ejemplo, para añadir Viernes Santo si tu distribuidora lo trata como P3, o para pruebas).

La resolución de festivos sigue un orden de prioridad de tres capas:
1. **JSON override** (`/config/pvpc_festivos_p3.json`) — máxima prioridad, para correcciones manuales
2. **Datos originales de aiopvpc** — el diccionario hardcodeado (2021–2025) se preserva por compatibilidad
3. **Cálculo automático** — fallback para cualquier año no cubierto, funciona para siempre

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

> **Nota:** Copiar `pvpc_festivos_p3.json` **no es necesario**. Los festivos se calculan automáticamente. El fichero JSON solo se necesita si quieres sobreescribir fechas manualmente (por ejemplo, añadir Viernes Santo para tu distribuidora).

### Paso 4 — Verificar

Comprueba los logs en **Ajustes → Sistema → Registros**. Deberías ver:

```
INFO [...] PVPC festivos P3: años precargados [2021, 2022, 2023, 2024, 2025], años futuros se calcularán automáticamente (JSON override: no encontrado)
```

Cuando la integración consulte 2026 por primera vez:

```
INFO [...] Festivos P3 calculados automáticamente para 2026: ['2026-01-01', '2026-01-06', '2026-05-01', '2026-10-12', '2026-12-08', '2026-12-25', '2027-01-01', '2027-01-06']
```

---

## Base legal: ¿qué se considera P3?

La definición del periodo P3 (valle) viene de la **Circular 3/2020 de la CNMC** ([BOE-A-2020-1066](https://www.boe.es/buscar/doc.php?id=BOE-A-2020-1066)), que establece la metodología para el cálculo de los peajes de transporte y distribución de electricidad:

> *«Se consideran como horas del periodo 3 (valle) todas las horas de los sábados, domingos, el 6 de enero y los días festivos de ámbito nacional, definidos como tales en el calendario oficial del año correspondiente, **con exclusión tanto de los festivos sustituibles como de los que no tienen fecha fija**.»*

Esto significa:

### ✅ P3 (24h valle) — Festivos nacionales no sustituibles con fecha fija

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

> **Nota:** Cuando un festivo de fecha fija cae en fin de semana (sábado o domingo), ya es P3 por defecto y no necesita estar listado aparte. Por ejemplo, en 2026: 15 de agosto (SÁB), 1 de noviembre (DOM) y 6 de diciembre (DOM) se excluyen de la lista calculada porque ya son P3 como días de fin de semana.

### ❌ Viernes Santo — Excluido del P3

El Viernes Santo es un **festivo nacional no sustituible**, pero **no tiene fecha fija** (depende de la Pascua). La Circular de la CNMC excluye explícitamente los festivos sin fecha fija del P3.

Esto está confirmado con datos reales de facturación: e-distribución factura el Viernes Santo con periodos P1/P2 durante el día, no como P3 todo el día (verificado con curvas de carga del 03-04-2026).

Si tu distribuidora sí trata el Viernes Santo como P3, puedes añadirlo mediante el fichero JSON de override (ver más abajo).

### ❌ Nunca P3

- **Festivos autonómicos** (Comunidad Autónoma): aunque sea festivo en tu comunidad, la electricidad se factura a tarifas normales P1/P2/P3 de día laborable
- **Festivos locales** (municipales): igual que los autonómicos
- **Festivos nacionales sustituibles** que una CCAA haya reemplazado por otro

La tarifa PVPC se aplica a **nivel nacional**, no autonómico. Tu distribuidora no ajusta los periodos P3 según el calendario de tu comunidad autónoma.

---

## Opcional: fichero JSON de override

Si necesitas sobreescribir los festivos calculados automáticamente, crea `/config/pvpc_festivos_p3.json`.

**Ejemplo: añadir Viernes Santo** para distribuidoras que lo tratan como P3:

```json
{
  "2026": [
    "2026-01-01", "2026-01-06", "2026-04-03", "2026-05-01",
    "2026-10-12", "2026-12-08", "2026-12-25"
  ]
}
```

**Ejemplo: usar los 9 festivos de fecha fija** (sin exclusión de fin de semana ni lookahead — enfoque más simple):

```json
{
  "2026": [
    "2026-01-01", "2026-01-06", "2026-05-01", "2026-08-15",
    "2026-10-12", "2026-11-01", "2026-12-06", "2026-12-08",
    "2026-12-25"
  ]
}
```

Cuando el fichero JSON existe, sus fechas tienen prioridad sobre el cálculo automático para los años que contiene. Los años que no están en el JSON se siguen calculando automáticamente.

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

> **Nota:** El endpoint de seg-social.es (`CalendarioServlet?exportacion=CSV&tipo=0`) requiere sesión de navegador (cookie JSESSIONID). Las llamadas directas con `curl` sin cookies devuelven respuestas vacías (HTTP 200, Content-Length: 0). El CSV debe descargarse manualmente desde la web.

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

### v0.3.0
- **Viernes Santo excluido** del cálculo automático según Circular 3/2020 de la CNMC (no tiene fecha fija). Confirmado con datos reales de facturación de e-distribución (crédito: @tmallafre). Se puede añadir de nuevo mediante JSON override.
- **Festivos en fin de semana excluidos** — los festivos que caen en sábado/domingo ya son P3 como días de fin de semana
- **Lookahead del año siguiente** — se incluyen 1 y 6 de enero de year+1 para la transición de año
- Cálculo verificado con resultados idénticos a `spanish-pvpc-holidays` de @privatecoder

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
