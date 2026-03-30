"""The pvpc_hourly_pricing integration - Patched with external JSON holidays.

Parche para corregir el KeyError en aiopvpc cuando el año actual no está
en el diccionario hardcodeado _NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD.

En lugar de usar defaultdict(set) vacío (que pierde la info de festivos),
esta versión carga los festivos desde un fichero JSON externo editable:
  /config/pvpc_festivos_p3.json

Si el fichero no existe o el año no está en él, se usa set() vacío como
fallback (equivalente al parche defaultdict original).

Más info: https://github.com/home-assistant/core/issues/160084
"""

import json
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

from homeassistant.const import CONF_API_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .coordinator import ElecPricesDataUpdateCoordinator, PVPCConfigEntry
from .helpers import get_enabled_sensor_keys

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

# Ruta del fichero JSON con los festivos nacionales P3
_HOLIDAYS_JSON = Path("/config/pvpc_festivos_p3.json")


def _load_holidays_from_json() -> dict[int, set[date]]:
    """Load national P3 holidays from external JSON file.

    Returns a dict {year: set(date, ...)} compatible with
    aiopvpc's _NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD format.
    """
    holidays: dict[int, set[date]] = {}

    if not _HOLIDAYS_JSON.is_file():
        _LOGGER.warning(
            "Fichero de festivos no encontrado: %s — "
            "los festivos nacionales NO se aplicarán como P3. "
            "Descarga el fichero desde el repositorio del parche.",
            _HOLIDAYS_JSON,
        )
        return holidays

    try:
        raw = json.loads(_HOLIDAYS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as err:
        _LOGGER.error(
            "Error leyendo %s: %s — usando festivos vacíos", _HOLIDAYS_JSON, err
        )
        return holidays

    for year_str, dates_list in raw.items():
        # Saltar claves que empiezan por _ (metadatos)
        if year_str.startswith("_"):
            continue
        try:
            year = int(year_str)
        except ValueError:
            continue

        year_dates: set[date] = set()
        for d in dates_list:
            try:
                year_dates.add(date.fromisoformat(d))
            except (ValueError, TypeError):
                _LOGGER.warning("Fecha inválida en %s: %s", year_str, d)
        holidays[year] = year_dates

    _LOGGER.info(
        "Festivos P3 cargados desde %s: años %s",
        _HOLIDAYS_JSON,
        sorted(holidays.keys()),
    )
    return holidays


async def async_setup_entry(hass: HomeAssistant, entry: PVPCConfigEntry) -> bool:
    """Set up pvpc hourly pricing from a config entry."""

    # --- PARCHE: Sustituir el diccionario hardcodeado de festivos ---
    try:
        import aiopvpc.pvpc_tariff as pvpc_tariff

        # Cargar festivos desde JSON externo
        json_holidays = _load_holidays_from_json()

        if json_holidays:
            # Mezclar: JSON tiene prioridad, pero conservar años del original
            # que no estén en el JSON (por si aiopvpc se actualiza algún día)
            merged = dict(pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD)
            merged.update(json_holidays)
            pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD = defaultdict(
                set, merged
            )
        else:
            # Fallback: al menos evitar el KeyError con defaultdict vacío
            pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD = defaultdict(
                set, pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD
            )

    except (ImportError, AttributeError, TypeError) as err:
        _LOGGER.warning("No se pudo parchear aiopvpc: %s", err)

    # --- FIN PARCHE ---

    entity_registry = er.async_get(hass)
    sensor_keys = get_enabled_sensor_keys(
        using_private_api=entry.data.get(CONF_API_TOKEN) is not None,
        entries=er.async_entries_for_config_entry(entity_registry, entry.entry_id),
    )
    coordinator = ElecPricesDataUpdateCoordinator(hass, entry, sensor_keys)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PVPCConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
