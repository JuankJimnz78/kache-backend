import re
import unicodedata


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre de producto para usarlo como clave de comparación
    entre comercios: minúsculas, sin tildes, sin espacios repetidos ni
    espacios al inicio/fin. No se usa para mostrar, solo para matching.
    """
    if not nombre:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sin_tildes.lower().strip())


# Marcas nacionales confirmadas en el catálogo real de más de un comercio
# (ver diagnóstico de Aceites/Arroz entre Supermaxi y Coral). Cada marca
# mapea a sus variantes de escritura observadas en los sitios.
MARCAS_CONOCIDAS = {
    "la favorita": ["la favorita", "favorita"],
    "casa del arroz": ["casa del arroz"],
    "banquete": ["banquete"],
    "arbolito": ["arbolito"],
    "ecolove": ["ecolove"],
    "alesol": ["alesol"],
    "real": ["real"],
    "pintuco": ["pintuco"],
    "pinturas unidas": ["pinturas unidas", "unidas"],
    "condor": ["condor"],
    # Farmacia: confirmadas por interseccion real entre Cruz Azul y Fybeca
    # (campo `marca` de cada scraper), mas Bonadol/Analgan detectadas a mano
    # (su `marca` no siempre viene poblada en el sitio, pero el texto del
    # nombre sigue conteniendo la marca literal).
    "bonadol": ["bonadol"],
    "analgan": ["analgan"],
    "acetagen": ["acetagen"],
    "apronax": ["apronax"],
    "apyral": ["apyral"],
    "buprex": ["buprex"],
    "elbrus": ["elbrus"],
    "energit": ["energit"],
    "fakulti": ["fakulti"],
    "febroxial": ["febroxial"],
    "feroglobin": ["feroglobin"],
    "frizac": ["frizac"],
    "ibufen": ["ibufen"],
    "luvit": ["luvit"],
    "napafen": ["napafen"],
    "nature's garden": ["nature's garden"],
    "orange c": ["orange c"],
    "paralgen": ["paralgen"],
    "profinal": ["profinal"],
    "recom-b": ["recom-b"],
    "redoxon": ["redoxon"],
    "resaquit": ["resaquit"],
    "umbral": ["umbral"],
    "umbramil": ["umbramil"],
    "x ray": ["x ray", "xray"],
}


def detectar_marca(nombre_normalizado: str) -> str:
    """
    Busca alguna marca conocida dentro de un nombre ya normalizado
    (ver normalizar_nombre). Devuelve la marca canónica encontrada o ""
    si ninguna calza. Se usa como parte de la clave de matching cuando
    el nombre completo no coincide entre comercios porque cada uno
    redacta el nombre distinto (mismo producto, misma marca).
    """
    for marca_canonica, variantes in MARCAS_CONOCIDAS.items():
        for variante in sorted(variantes, key=len, reverse=True):
            if re.search(rf"\b{re.escape(variante)}\b", nombre_normalizado):
                return marca_canonica
    return ""


_UNIDADES_VOLUMEN = {
    "ml": 1,
    "l": 1000,
    "litro": 1000,
    "litros": 1000,
    "gl": 3785.41,
    "gal": 3785.41,
    "galon": 3785.41,
    "galones": 3785.41,
}
_UNIDADES_PESO = {
    "g": 1,
    "gr": 1,  # abreviatura de "gramo" muy común en nombres de farmacia
    "kg": 1000,
    "kilo": 1000,
    "kilos": 1000,
    "lb": 453.592,
    "libra": 453.592,
    "libras": 453.592,
}

# Orden importa: las unidades más largas van primero para que no las
# "tape" un prefijo corto (ej. "libras" no debe resolverse como "l").
_PATRON_CANTIDAD = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(ml|kg|kilos?|lb|libras?|litros?|galones?|gal|gl|gr|l|g)\b"
)


def extraer_cantidad_normalizada(nombre: str) -> str:
    """
    Extrae la presentación (volumen o peso) del nombre del producto y la
    convierte a una unidad canónica (ml o g) para poder comparar
    presentaciones escritas distinto entre comercios (ej. "1L" y
    "1000 Ml" deben dar la misma clave). Devuelve "" si no encuentra
    ningún patrón reconocible.
    """
    if not nombre:
        return ""
    texto = nombre.lower().replace(",", ".")
    texto = re.sub(r"(?<=\d) (?=\d{3}\b)", "", texto)  # "1 000" -> "1000"

    match = _PATRON_CANTIDAD.search(texto)
    if not match:
        return ""

    valor = float(match.group(1))
    unidad = match.group(2)

    if unidad in _UNIDADES_VOLUMEN:
        return f"volumen:{round(valor * _UNIDADES_VOLUMEN[unidad])}"
    if unidad in _UNIDADES_PESO:
        return f"peso:{round(valor * _UNIDADES_PESO[unidad])}"
    return ""


# ── Farmacia: dosis (mg/gr) y conteo de unidades (x24, C/50) ───────────
#
# En farmacia, "cantidad" (volumen/peso del envase) casi nunca describe el
# producto de forma confiable: lo que distingue una presentación de otra es
# la dosis por unidad (500 Mg, 1 Gr) y cuántas unidades trae la caja (x24,
# C/50). Son dos dimensiones separadas y DELIBERADAMENTE no se mezclan con
# volumen/peso: fusionar "500 Mg" con un peso de envase sería comparar cosas
# distintas (dosis por cápsula vs. contenido total).

_UNIDADES_DOSIS = {
    "mg": 1,
    "mcg": 0.001,
    "ug": 0.001,
    "gr": 1000,
    "g": 1000,
}

_PATRON_DOSIS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|mcg|ug|gr|g)\b")


def extraer_dosis_normalizada(nombre: str) -> str:
    """
    Extrae todas las dosis (mg/mcg/gr/g) del nombre -- puede haber más de
    una en combinaciones (ej. "325/37.5 Mg"), cada una se convierte a mg y
    se arma una firma ordenada para poder comparar aunque los ingredientes
    aparezcan en otro orden en el otro sitio. Devuelve "" si no encuentra
    ninguna dosis.
    """
    if not nombre:
        return ""
    texto = nombre.lower().replace(",", ".")

    valores = []
    for match in _PATRON_DOSIS.finditer(texto):
        valor = float(match.group(1))
        unidad = match.group(2)
        valores.append(valor * _UNIDADES_DOSIS[unidad])

    if not valores:
        return ""

    valores.sort()
    return "+".join(f"{v:g}" for v in valores)



# Unidades que, si aparecen justo después del número, indican que en
# realidad es una dosis/medida pegada al mismo separador "x"/"c/" (ej.
# "x500Mg", "x 65 mg", "x 800 UI") y no un conteo de unidades. Ojo: no se
# excluye por "cualquier palabra siguiente" (eso rechazaría de más, ej.
# "x 10 tabletas" sí es un conteo real) -- solo por unidades de medida.
_UNIDADES_NO_CONTEO = r"(?:mg|mcg|ug|gr|g|ml|l|kg|lb|gal|ui|iu)"

_PATRON_CONTEO = re.compile(
    rf"(?:\bx|c/)\s*(\d+)\b(?!\s*{_UNIDADES_NO_CONTEO}\b)", re.IGNORECASE
)


def extraer_conteo_normalizado(nombre: str) -> str:
    """
    Extrae cuántas unidades (cápsulas/tabletas/etc.) trae el empaque, de
    patrones tipo "x24", "X 24", "C/24", "c/50". El lookahead negativo evita
    confundir esto con una dosis pegada al mismo separador (ej. "x500Mg" o
    "x 65 mg" no cuentan como conteo, son dosis). Devuelve "" si no
    encuentra ningún patrón reconocible.
    """
    if not nombre:
        return ""
    match = _PATRON_CONTEO.search(nombre)
    if not match:
        return ""
    return match.group(1)


# ── Filtro extra para el fallback marca+cantidad ────────────────────────
#
# marca_normalizada + cantidad_normalizada por sí solas no distinguen líneas
# de producto distintas de la misma marca y presentación (ej. una pintura
# "para canchas" y un esmalte estándar, ambos Cóndor 1gl). Antes de aceptar
# un match por esa vía, se exige además que los nombres compartan alguna
# palabra más allá de marca y unidad -- no se excluyen palabras genéricas de
# categoría (ej. "arroz", "pintura") por ahora, eso queda fuera de alcance.
#
# Sí se excluyen artículos/preposiciones/conjunciones puras (sin ningún
# contenido que describa el producto): sin esto, dos nombres cualesquiera
# comparten casi siempre "de"/"en"/"y" y la condición queda vacía de
# sentido (se detectó al probar el caso Sellamur vs. Metaltec, que de otro
# modo "compartía" la palabra "en").
_PALABRAS_VACIAS_MATCHING = {
    "de", "del", "la", "las", "el", "los", "en", "y", "o", "u", "a",
    "con", "sin", "para", "por", "al",
}

_PALABRAS_UNIDAD_MATCHING = (
    set(_UNIDADES_VOLUMEN) | set(_UNIDADES_PESO) | set(_UNIDADES_DOSIS)
)


def _palabras_mas_alla_de_marca_y_cantidad(nombre_normalizado: str, marca_canonica: str) -> set:
    tokens = re.findall(r"[a-z]+", nombre_normalizado)
    variantes_marca = set()
    if marca_canonica:
        for variante in MARCAS_CONOCIDAS.get(marca_canonica, []):
            variantes_marca.update(variante.split())
    return {
        t for t in tokens
        if t not in variantes_marca
        and t not in _PALABRAS_UNIDAD_MATCHING
        and t not in _PALABRAS_VACIAS_MATCHING
    }


def comparten_palabra_clave(nombre_normalizado_a: str, nombre_normalizado_b: str, marca_canonica: str) -> bool:
    """
    True si, más allá de marca y unidades de cantidad, los dos nombres (ya
    normalizados con normalizar_nombre) comparten al menos una palabra.
    Se usa como filtro adicional al fusionar por marca+cantidad_normalizada
    entre comercios -- no se usa en el matching por dosis+conteo (farmacia),
    que ya exige coincidencia exacta en ambos campos.
    """
    a = _palabras_mas_alla_de_marca_y_cantidad(nombre_normalizado_a, marca_canonica)
    b = _palabras_mas_alla_de_marca_y_cantidad(nombre_normalizado_b, marca_canonica)
    return bool(a & b)
