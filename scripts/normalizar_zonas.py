#!/usr/bin/env python3
"""
normalizar_zonas.py — etiquetado masivo de zona_normalizada en propiedades_mercado.

Corre una sola vez sobre los datos existentes. Luego el scraper lo usa en tiempo real.
Para re-correr: python3 scripts/normalizar_zonas.py [--dry-run] [--reset]

--dry-run   muestra conteos sin escribir en Supabase
--reset     limpia zona_normalizada antes de re-etiquetar (útil para actualizar el diccionario)
"""

import sys
import re
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
ENV_FILE = SCRIPT_DIR / ".env"

SUPABASE_TABLE = "propiedades_mercado"
BATCH_SIZE = 200


# ── Taxonomía de zonas ─────────────────────────────────────────────────────────
# Orden de prioridad: primero keywords más específicos, Otros Tandil como fallback.
# Cada regla es (zona_normalizada, [keywords])
# El matching es case-insensitive sobre la concatenación de zona+titulo+descripcion.

FUERA_DE_TANDIL_KEYWORDS = [
    "capital federal", "caba", "almagro", "palermo", "belgrano caba",
    "caballito", "villa urquiza", "boedo", "flores", "san telmo",
    "la plata", "mar del plata", "bahía blanca", "necochea", "azul",
    "olavarría", "ayacucho", "balcarce", "lobería", "rauch",
]

ZONA_RULES = [
    # Zonas muy específicas primero
    ("Barrio Dique",          ["dique"]),
    ("Barrio Galicia",        ["villa galicia", "barrio galicia", "galicia", "bulewski"]),
    ("Barrio Graduados",      ["graduados"]),
    ("La Mata",               ["la mata"]),
    ("Countries",             ["country", "valle escondido", "sierras de tandil",
                               "club edal", "entre las sierras", "barrio golf"]),
    ("Sierras / Cerros",      ["cerro leones", "peñasco", "las piedras", "el centinela",
                               "sierra", "cerro", "sierras"]),
    # Corredores (avenidas principales)
    ("Corredor Avellaneda",   ["avellaneda"]),
    ("Corredor Brasil",       ["brasil"]),
    ("Corredor Santamarina",  ["santamarina"]),
    ("Corredor Juan B. Justo", ["juan b. justo", "justo"]),
    # Semicentro antes que Centro para evitar falsos positivos
    ("Semicentro",            ["semicentro", "av. paz", "españa", "uriburu", "maipú"]),
    # Centro
    ("Centro",                ["centro", "fuerte independencia", "pinto",
                               "9 de julio", "rodríguez"]),
    # Zona Norte (calle Justo con numeración alta — requiere heurística especial)
    ("Zona Norte",            ["buzón"]),
]


def load_env():
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def normalizar_zona(zona: str, titulo: str, descripcion: str):
    """
    Retorna (zona_normalizada, fuera_de_tandil).
    zona_normalizada puede ser None si no hay match (se deja para refinamiento posterior).
    """
    texto = " ".join(filter(None, [zona, titulo, descripcion])).lower()

    # Primero verificar si es fuera de Tandil
    for kw in FUERA_DE_TANDIL_KEYWORDS:
        if kw in texto:
            return None, True

    # Aplicar reglas de zona en orden de prioridad
    for zona_norm, keywords in ZONA_RULES:
        for kw in keywords:
            if kw in texto:
                return zona_norm, False

    # Si llegó hasta acá y el texto menciona Tandil (o es de fuentes que son 100% Tandil)
    # lo clasificamos como Otros Tandil
    if "tandil" in texto or zona.strip():
        return "Otros Tandil", False

    return None, False


def fetch_all_properties(supabase_url: str, service_key: str) -> list[dict]:
    """Descarga todas las propiedades con paginación."""
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Range-Unit": "items",
    }
    offset = 0
    all_props = []

    while True:
        url = (
            f"{supabase_url}/rest/v1/{SUPABASE_TABLE}"
            f"?select=id,zona,titulo,descripcion,zona_normalizada,fuera_de_tandil"
            f"&order=id.asc"
            f"&offset={offset}&limit={BATCH_SIZE}"
        )
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read())
        except Exception as e:
            print(f"  Error al leer propiedades (offset={offset}): {e}", file=sys.stderr)
            break

        if not batch:
            break

        all_props.extend(batch)
        print(f"  Leídas {len(all_props)} propiedades...", end="\r")

        if len(batch) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print()
    return all_props


def update_batch(rows: list[dict], supabase_url: str, service_key: str) -> int:
    """
    Actualiza zona_normalizada y fuera_de_tandil vía PATCH individual (Supabase no soporta
    bulk PATCH por IDs distintos). Agrupa por zona_normalizada para minimizar requests.
    Retorna cantidad de filas actualizadas.
    """
    from collections import defaultdict

    # Agrupar por (zona_normalizada, fuera_de_tandil) para hacer menos requests
    groups: dict[tuple, list[str]] = defaultdict(list)
    for row in rows:
        key = (row["zona_normalizada"], row["fuera_de_tandil"])
        groups[key].append(row["id"])

    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    updated = 0
    for (zona_norm, fuera), ids in groups.items():
        # Supabase soporta filtro ?id=in.(uuid1,uuid2,...) para PATCH bulk
        ids_str = ",".join(ids)
        url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?id=in.({ids_str})"
        body = json.dumps({
            "zona_normalizada": zona_norm,
            "fuera_de_tandil": fuera,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
        try:
            with urllib.request.urlopen(req, timeout=30):
                updated += len(ids)
        except urllib.error.HTTPError as e:
            print(f"  Error PATCH {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"  Error PATCH: {e}", file=sys.stderr)

    return updated


def main():
    parser = argparse.ArgumentParser(description="Normalizar zonas en propiedades_mercado")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en Supabase")
    parser.add_argument("--reset", action="store_true",
                        help="Limpiar zona_normalizada antes de re-etiquetar")
    args = parser.parse_args()

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("ERROR: Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env", file=sys.stderr)
        sys.exit(1)

    print("=== Normalización de zonas Tandil ===")

    if args.reset and not args.dry_run:
        print("Limpiando zona_normalizada...")
        url = f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?id=neq.00000000-0000-0000-0000-000000000000"
        req = urllib.request.Request(
            url,
            data=json.dumps({"zona_normalizada": None, "fuera_de_tandil": False}).encode(),
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=30):
            pass
        print("  ✓ Limpieza completa")

    print("Descargando propiedades...")
    props = fetch_all_properties(supabase_url, service_key)
    print(f"Total propiedades: {len(props)}")

    # Etiquetar
    stats: dict[str, int] = {}
    to_update = []
    skipped = 0

    for p in props:
        zona_norm, fuera = normalizar_zona(
            p.get("zona") or "",
            p.get("titulo") or "",
            p.get("descripcion") or "",
        )

        # Si ya tiene valor y no se pidió reset, saltar
        if not args.reset and p.get("zona_normalizada") is not None:
            skipped += 1
            continue

        stats[zona_norm or "(sin zona)"] = stats.get(zona_norm or "(sin zona)", 0) + 1
        if not args.dry_run:
            to_update.append({
                "id": p["id"],
                "zona_normalizada": zona_norm,
                "fuera_de_tandil": fuera,
            })

    print(f"\nEtiquetado completado:")
    for zona, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {zona:<30} {count:>5}")
    print(f"  {'Sin cambios (ya etiquetadas)':<30} {skipped:>5}")
    print(f"  {'TOTAL a actualizar':<30} {len(to_update):>5}")

    if args.dry_run:
        print("\n[DRY RUN] No se escribió nada.")
        return

    if to_update:
        print("\nEscribiendo en Supabase...")
        # Procesar en lotes para no generar URLs demasiado largas
        batch_size = 50
        total_updated = 0
        for i in range(0, len(to_update), batch_size):
            batch = to_update[i: i + batch_size]
            updated = update_batch(batch, supabase_url, service_key)
            total_updated += updated
            print(f"  Lote {i // batch_size + 1}: {updated}/{len(batch)} actualizadas")

        print(f"\n✓ Total actualizadas: {total_updated}/{len(to_update)}")
    else:
        print("\nNo hay propiedades para actualizar.")


if __name__ == "__main__":
    main()
