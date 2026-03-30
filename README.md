# PVPC Hourly Pricing — Parche con festivos P3 en JSON externo

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HA version](https://img.shields.io/badge/HA-2024.6%2B-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Parche para la integración oficial `pvpc_hourly_pricing` de Home Assistant, que dejó de funcionar el 1 de enero de 2026 por un bug en la librería `aiopvpc`.

## ¿Qué problema resuelve?

La librería `aiopvpc` tiene los festivos nacionales de España **hardcodeados** en un diccionario Python que solo llega hasta 2025. Al entrar en 2026, lanza un `KeyError: 2026` y la integración deja de funcionar completamente.

### ¿Por qué este parche y no otro?

| Solución | Evita crash | Festivos correctos | Actualizable sin código |
|----------|:-----------:|:------------------:|:----------------------:|
| `defaultdict(set)` (HA-PVPC-Updated) | ✅ | ❌ festivos vacíos para 2026+ | ❌ |
| ha-pvpc-next | ✅ | ✅ | ✅ pero es integración nueva |
| **Este parche (JSON externo)** | ✅ | ✅ | ✅ editar un fichero JSON |

El parche `defaultdict(set)` evita el crash, pero al devolver un set vacío para 2026+, **días como el 1 de mayo o el 12 de octubre no se marcan como P3 (valle)**. Esos días se facturan incorrectamente a tarifa P1/P2.

Este parche carga los festivos desde un fichero JSON editable (`/config/pvpc_festivos_p3.json`), con los datos correctos de 2021 a 2027 incluidos.

## Instalación

### Paso 1 — Copiar la integración oficial

Necesitas copiar los ficheros de la integración del core al directorio `custom_components`. Accede por SSH y ejecuta:

```bash
mkdir -p /config/custom_components
docker cp homeassistant:/usr/src/homeassistant/homeassistant/components/pvpc_hourly_pricing \
  /config/custom_components/
```

### Paso 2 — Instalar este parche vía HACS

1. En Home Assistant, abre **HACS → Integraciones**
2. Menú ⋮ → **Repositorios personalizados**
3. Añade la URL de este repositorio como **Integración**
4. Busca **PVPC Hourly Pricing — JSON Holidays Fix** e instala
5. Esto sobreescribirá el `__init__.py` y `manifest.json` con las versiones parcheadas

### Paso 3 — Copiar el fichero de festivos

Copia `pvpc_festivos_p3.json` a la raíz de tu configuración:

```bash
cp /config/custom_components/pvpc_hourly_pricing/pvpc_festivos_p3.json /config/
```

### Paso 4 — Reiniciar

```bash
ha core restart
```

### Verificación

En los logs de HA debería aparecer:

```
INFO [...] Festivos P3 cargados desde /config/pvpc_festivos_p3.json: años [2021, 2022, 2023, 2024, 2025, 2026, 2027]
```

## Actualización anual

Cada año, cuando el BOE publique el calendario laboral (normalmente en octubre), edita `/config/pvpc_festivos_p3.json` y añade el nuevo año:

```json
"2028": [
    "2028-01-01",
    "2028-01-06",
    "2028-04-14",
    "2028-05-01",
    "2028-08-15",
    "2028-10-12",
    "2028-11-01",
    "2028-12-06",
    "2028-12-08",
    "2028-12-25"
]
```

**Solo cambia la fecha de Viernes Santo cada año.** Los otros 9 festivos son siempre los mismos:

| Festivo | Fecha |
|---------|-------|
| Año Nuevo | 1 enero |
| Epifanía | 6 enero |
| Viernes Santo | *variable* |
| Día del Trabajo | 1 mayo |
| Asunción | 15 agosto |
| Fiesta Nacional | 12 octubre |
| Todos los Santos | 1 noviembre |
| Constitución | 6 diciembre |
| Inmaculada | 8 diciembre |
| Navidad | 25 diciembre |

## Desinstalación

Cuando HA Core integre un fix oficial:

```bash
rm -r /config/custom_components/pvpc_hourly_pricing
rm /config/pvpc_festivos_p3.json
```

Reinicia HA y la integración oficial volverá a tomar el control.

## Contexto

- [Issue #160084](https://github.com/home-assistant/core/issues/160084) — Primer reporte del bug
- [Issue #161231](https://github.com/home-assistant/core/issues/161231) — Confirmación
- [Issue #162550](https://github.com/home-assistant/core/issues/162550) — Petición de actualización
- [BOE — Festivos 2026](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667)

## Licencia

MIT — Misma licencia que la integración original y que `aiopvpc`.
