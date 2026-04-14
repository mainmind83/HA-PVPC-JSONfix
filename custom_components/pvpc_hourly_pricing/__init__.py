"""The pvpc_hourly_pricing integration - Patched with automatic P3 holiday calculation.

Parche para corregir el KeyError en aiopvpc cuando el año actual no está
en el diccionario hardcodeado _NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD.

Esta versión calcula los festivos nacionales P3 automáticamente para
cualquier año, sin depender de ficheros externos ni endpoints:
  - 9 festivos con fecha fija (mismo día cada año)
  - Excluye Viernes Santo (no tiene fecha fija, excluido por CNMC Circular
    3/2020 y confirmado por datos reales de distribuidoras como e-distribución)
  - Excluye festivos que caen en fin de semana (ya son P3 por ser sáb/dom)
  - Añade festivos del 1 y 6 de enero del año siguiente (lookahead)

Opcionalmente, si existe /config/pvpc_festivos_p3.json, se usa como
override manual (por ejemplo para añadir Viernes Santo u otros festivos).

Basado en aportaciones de @privatecoder (spanish-pvpc-holidays) y datos
reales de facturación de @tmallafre (e-distribución).

Más info: https://github.com/mainmind83/HA-PVPC-JSONfix
"""

import json
import logging
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from homeassistant.const import CONF_API_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .coordinator import ElecPricesDataUpdateCoordinator, PVPCConfigEntry
from .helpers import get_enabled_sensor_keys

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

# Ruta del fichero JSON opcional con festivos manuales (override)
_HOLIDAYS_JSON = Path("/config/pvpc_festivos_p3.json")


def _easter_date(year: int) -> date:
    """Calculate Easter Sunday date using the Anonymous Gregorian algorithm.

    Also known as the "Meeus/Jones/Butcher" algorithm.
    Valid for any year in the Gregorian calendar.
    Reference: https://en.wikipedia.org/wiki/Date_of_Easter#Anonymous_Gregorian_algorithm
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _good_friday(year: int) -> date:
    """Calculate Good Friday (Viernes Santo) for a given year."""
    return _easter_date(year) - timedelta(days=2)


def _calculate_p3_holidays(year: int) -> set[date]:
    """Calculate all national P3 holidays for a given year.

    Per CNMC Circular 3/2020 (BOE-A-2020-1066), P3 (valley) applies to:
    - Saturdays and Sundays (handled separately by aiopvpc)
    - National holidays with fixed date, non-substitutable
    - January 6th (Epiphany, kept by all autonomous communities)

    Excluded per regulation:
    - Good Friday: non-substitutable but NO fixed date → not P3
      (confirmed by real billing data from e-distribución)
    - Holidays falling on weekends: already P3 as sat/sun
    - Substitutable holidays replaced by CCAA
    - Regional and local holidays

    Next-year lookahead: Jan 1 and Jan 6 of year+1 are included
    to cover the transition period (credit: @privatecoder).
    """
    # All 9 fixed-date national P3 holidays
    candidates = {
        date(year, 1, 1),     # Año Nuevo
        date(year, 1, 6),     # Epifanía del Señor
        date(year, 5, 1),     # Fiesta del Trabajo
        date(year, 8, 15),    # Asunción de la Virgen
        date(year, 10, 12),   # Fiesta Nacional de España
        date(year, 11, 1),    # Todos los Santos
        date(year, 12, 6),    # Día de la Constitución
        date(year, 12, 8),    # Inmaculada Concepción
        date(year, 12, 25),   # Natividad del Señor
    }

    # NOTE: Good Friday intentionally NOT included.
    # CNMC Circular 3/2020 excludes holidays without fixed date.
    # Confirmed by e-distribución billing data (P1/P2 on Good Friday).
    # Users can add it via JSON override if their distributor treats it as P3.

    # Exclude holidays falling on weekends (already P3 as sat/sun)
    holidays = {d for d in candidates if d.weekday() < 5}  # 0=Mon..4=Fri

    # Next-year lookahead: add Jan 1 and Jan 6 of following year
    next_jan_1 = date(year + 1, 1, 1)
    next_jan_6 = date(year + 1, 1, 6)
    if next_jan_1.weekday() < 5:
        holidays.add(next_jan_1)
    if next_jan_6.weekday() < 5:
        holidays.add(next_jan_6)

    return holidays


def _load_json_overrides() -> dict[int, set[date]]:
    """Load optional manual holiday overrides from JSON file.

    If the file exists, its holidays are merged with the calculated ones.
    This allows users to add regional holidays or correct any discrepancy.
    """
    if not _HOLIDAYS_JSON.is_file():
        return {}

    try:
        raw = json.loads(_HOLIDAYS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as err:
        _LOGGER.warning(
            "Error leyendo %s: %s — se ignorará", _HOLIDAYS_JSON, err
        )
        return {}

    overrides: dict[int, set[date]] = {}
    for year_str, dates_list in raw.items():
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
                pass
        overrides[year] = year_dates

    _LOGGER.debug(
        "Festivos P3 override desde %s: años %s",
        _HOLIDAYS_JSON,
        sorted(overrides.keys()),
    )
    return overrides


def _build_holidays_dict(
    original: dict, overrides: dict[int, set[date]]
) -> dict[int, set[date]]:
    """Build the complete holidays dictionary.

    Priority: JSON overrides > calculated > original hardcoded.
    For any year not in overrides, holidays are calculated automatically.
    """
    result: dict[int, set[date]] = {}

    # Start with original hardcoded data (years 2021-2025)
    for year, dates in original.items():
        result[year] = set(dates)

    # Override/extend with JSON file data
    for year, dates in overrides.items():
        result[year] = dates

    return result


class _AutoHolidaysDict(dict):
    """Dict subclass that auto-calculates holidays for missing years.

    When aiopvpc accesses _NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD[year]
    and the year is not in the dict, this class calculates the holidays
    on-the-fly instead of raising KeyError.
    """

    def __missing__(self, year: int) -> set[date]:
        """Auto-calculate P3 holidays for any missing year."""
        holidays = _calculate_p3_holidays(year)
        self[year] = holidays  # Cache for future lookups
        _LOGGER.info(
            "Festivos P3 calculados automáticamente para %d: %s",
            year,
            sorted(d.isoformat() for d in holidays),
        )
        return holidays


async def async_setup_entry(hass: HomeAssistant, entry: PVPCConfigEntry) -> bool:
    """Set up pvpc hourly pricing from a config entry."""

    # --- PARCHE: Sustituir el diccionario hardcodeado de festivos ---
    try:
        import aiopvpc.pvpc_tariff as pvpc_tariff

        # Cargar overrides opcionales desde JSON
        json_overrides = _load_json_overrides()

        # Construir diccionario base con datos originales + overrides
        base = _build_holidays_dict(
            pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD,
            json_overrides,
        )

        # Reemplazar con AutoHolidaysDict que calcula años faltantes
        auto_dict = _AutoHolidaysDict(base)
        pvpc_tariff._NATIONAL_EXTRA_HOLIDAYS_FOR_P3_PERIOD = auto_dict

        _LOGGER.info(
            "PVPC festivos P3: años precargados %s, "
            "años futuros se calcularán automáticamente "
            "(JSON override: %s)",
            sorted(auto_dict.keys()),
            "activo" if json_overrides else "no encontrado",
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
