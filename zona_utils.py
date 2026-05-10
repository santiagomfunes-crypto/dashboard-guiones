"""
zona_utils.py — Lógica de normalización de zonas para Tandil.
Importado por scraper_mercadolibre.py y scraper_casasdehoy.py.
"""

# ── Taxonomía de zonas ─────────────────────────────────────────────────────────
# Orden de prioridad: keywords específicos primero, Otros Tandil como fallback.

FUERA_DE_TANDIL_KEYWORDS = [
    "capital federal", "caba", "almagro", "palermo", "belgrano caba",
    "caballito", "villa urquiza", "boedo", "flores", "san telmo",
    "la plata", "mar del plata", "bahía blanca", "necochea", "azul",
    "olavarría", "ayacucho", "balcarce", "lobería", "rauch",
]

ZONA_RULES = [
    ("Barrio Dique",           ["dique"]),
    ("Barrio Galicia",         ["villa galicia", "barrio galicia", "galicia", "bulewski"]),
    ("Barrio Graduados",       ["graduados"]),
    ("La Mata",                ["la mata"]),
    ("Countries",              ["country", "valle escondido", "sierras de tandil",
                                "club edal", "entre las sierras", "barrio golf"]),
    ("Sierras / Cerros",       ["cerro leones", "peñasco", "las piedras", "el centinela",
                                "sierra", "cerro", "sierras"]),
    ("Corredor Avellaneda",    ["avellaneda"]),
    ("Corredor Brasil",        ["brasil"]),
    ("Corredor Santamarina",   ["santamarina"]),
    ("Corredor Juan B. Justo", ["juan b. justo", "justo"]),
    ("Semicentro",             ["semicentro", "av. paz", "españa", "uriburu", "maipú"]),
    ("Centro",                 ["centro", "fuerte independencia", "pinto",
                                "9 de julio", "rodríguez"]),
    ("Zona Norte",             ["buzón"]),
]


def normalizar_zona(zona: str, titulo: str, descripcion: str):
    """
    Retorna (zona_normalizada, fuera_de_tandil).

    - zona_normalizada: str con la zona clasificada, o None si no hay suficiente texto.
    - fuera_de_tandil: bool, True si la propiedad no es de Tandil.
    """
    texto = " ".join(filter(None, [zona, titulo, descripcion])).lower()

    if not texto.strip():
        return None, False

    for kw in FUERA_DE_TANDIL_KEYWORDS:
        if kw in texto:
            return None, True

    for zona_norm, keywords in ZONA_RULES:
        for kw in keywords:
            if kw in texto:
                return zona_norm, False

    # Cualquier cosa con texto pero sin match específico → Otros Tandil
    return "Otros Tandil", False
