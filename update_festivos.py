#!/usr/bin/env python3
"""
update_festivos.py — Actualiza pvpc_festivos_p3.json desde el CSV de la Seguridad Social.

Uso:
  1. Descarga el CSV desde la web de la Seguridad Social:
     - Abre https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/
     - Pulsa el botón de descarga/exportación CSV
     - Guarda el fichero como 'calendario.csv' en la misma carpeta que este script

  2. Ejecuta el script:
     python3 update_festivos.py calendario.csv

  3. El script actualiza /config/pvpc_festivos_p3.json añadiendo o actualizando
     los festivos nacionales del año que encuentre en el CSV.

  También se puede ejecutar desde SSH en Home Assistant:
     cd /config
     python3 update_festivos.py calendario.csv

Notas:
  - El CSV de seg-social.es tiene codificación Latin-1 (ISO-8859-1)
  - Solo se extraen las filas con TIPO = "Nacional"
  - Las fechas se convierten de DD-MM-YYYY a YYYY-MM-DD
  - Los festivos P3 según la regulación PVPC son los festivos nacionales
    no sustituibles + 6 de enero (Epifanía) + los que cada CCAA mantenga
  - Algunos festivos como Todos los Santos (1-nov) o Constitución (6-dic)
    pueden no aparecer como "Nacional" en el CSV si la CCAA los ha sustituido,
    pero son festivos P3 a nivel nacional igualmente. El script los añade
    automáticamente si no están en el CSV.
"""

import csv
import json
import sys
from datetime import date
from pathlib import Path

# Festivos P3 con fecha fija que SIEMPRE aplican a nivel nacional
# (independientemente de lo que diga el CSV de seg-social)
FESTIVOS_FIJOS_P3 = {
    (1, 1),    # Año Nuevo
    (1, 6),    # Epifanía del Señor
    (5, 1),    # Fiesta del Trabajo
    (8, 15),   # Asunción de la Virgen
    (10, 12),  # Fiesta Nacional de España
    (11, 1),   # Todos los Santos
    (12, 6),   # Día de la Constitución
    (12, 8),   # Inmaculada Concepción
    (12, 25),  # Natividad del Señor
}

# Ruta por defecto del JSON de festivos
DEFAULT_JSON_PATH = Path("/config/pvpc_festivos_p3.json")
# Alternativa si se ejecuta fuera de HA
LOCAL_JSON_PATH = Path(__file__).parent / "pvpc_festivos_p3.json"


def parse_csv(csv_path: str) -> dict[int, set[date]]:
    """Parse the seg-social CSV and extract national holidays by year."""
    holidays: dict[int, set[date]] = {}

    # Intentar varias codificaciones
    for encoding in ("latin-1", "utf-8", "cp1252"):
        try:
            with open(csv_path, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tipo = row.get("TIPO", "").strip()
                    fecha_str = row.get("FECHA", "").strip()

                    if tipo != "Nacional" or not fecha_str:
                        continue

                    # Formato DD-MM-YYYY
                    try:
                        parts = fecha_str.split("-")
                        d = date(int(parts[2]), int(parts[1]), int(parts[0]))
                    except (ValueError, IndexError):
                        print(f"  ⚠ Fecha inválida ignorada: {fecha_str}")
                        continue

                    if d.year not in holidays:
                        holidays[d.year] = set()
                    holidays[d.year].add(d)

                    desc = row.get("DESCRIPCION", "").strip().strip('"')
                    print(f"  ✓ {d.isoformat()} — {desc}")

            break  # Codificación correcta encontrada
        except UnicodeDecodeError:
            continue
    else:
        print(f"✗ No se pudo leer {csv_path} con ninguna codificación conocida")
        sys.exit(1)

    return holidays


def add_fixed_holidays(holidays: dict[int, set[date]]) -> dict[int, set[date]]:
    """Ensure all fixed P3 holidays are present for each year."""
    for year in holidays:
        for month, day in FESTIVOS_FIJOS_P3:
            fixed = date(year, month, day)
            if fixed not in holidays[year]:
                print(f"  + Añadido festivo fijo ausente: {fixed.isoformat()}")
                holidays[year].add(fixed)
    return holidays


def update_json(json_path: Path, new_holidays: dict[int, set[date]]) -> None:
    """Update the JSON file, merging new holidays with existing data."""
    # Leer JSON existente
    existing: dict = {}
    if json_path.is_file():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            print(f"\n📂 JSON existente: {json_path}")
            existing_years = [k for k in existing if not k.startswith("_")]
            print(f"   Años existentes: {sorted(existing_years)}")
        except (json.JSONDecodeError, OSError) as err:
            print(f"  ⚠ Error leyendo JSON existente: {err}")
            print("    Se creará uno nuevo")

    # Preservar metadatos
    metadata = {k: v for k, v in existing.items() if k.startswith("_")}

    # Convertir existentes a sets de dates
    all_holidays: dict[int, set[date]] = {}
    for year_str, dates_list in existing.items():
        if year_str.startswith("_"):
            continue
        try:
            year = int(year_str)
            all_holidays[year] = {date.fromisoformat(d) for d in dates_list}
        except (ValueError, TypeError):
            pass

    # Merge: nuevos datos sobreescriben años existentes
    for year, dates in new_holidays.items():
        action = "actualizado" if year in all_holidays else "añadido"
        all_holidays[year] = dates
        print(f"  {'↻' if action == 'actualizado' else '+'} {year} {action} ({len(dates)} festivos)")

    # Reconstruir JSON
    result: dict = {}
    # Metadatos primero
    result["_descripcion"] = (
        "Festivos nacionales de España que aplican periodo P3 (valle) "
        "24h completas en la tarifa PVPC 2.0TD. Actualizado con "
        "update_festivos.py desde el CSV de seg-social.es"
    )
    result["_formato"] = "YYYY-MM-DD"
    result["_ultima_actualizacion"] = date.today().isoformat()

    # Años ordenados
    for year in sorted(all_holidays.keys()):
        result[str(year)] = sorted(d.isoformat() for d in all_holidays[year])

    # Escribir
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n✅ JSON actualizado: {json_path}")
    print(f"   Años cubiertos: {sorted(all_holidays.keys())}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 update_festivos.py <calendario.csv>")
        print()
        print("Descarga el CSV desde:")
        print("  https://www.seg-social.es/wps/portal/wss/internet/CalendarioLaboral/")
        print("  (botón de exportación/descarga CSV)")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"📄 Leyendo CSV: {csv_path}")
    print()

    # 1. Parsear CSV
    holidays = parse_csv(csv_path)

    if not holidays:
        print("✗ No se encontraron festivos nacionales en el CSV")
        sys.exit(1)

    years = sorted(holidays.keys())
    print(f"\n📅 Años encontrados en CSV: {years}")

    # 2. Completar festivos fijos que puedan faltar
    print("\n🔧 Verificando festivos fijos P3...")
    holidays = add_fixed_holidays(holidays)

    # 3. Actualizar JSON
    json_path = DEFAULT_JSON_PATH if DEFAULT_JSON_PATH.parent.is_dir() else LOCAL_JSON_PATH
    print(f"\n📝 Actualizando JSON...")
    update_json(json_path, holidays)

    print("\n🎉 ¡Listo! Reinicia Home Assistant para aplicar los cambios.")


if __name__ == "__main__":
    main()
