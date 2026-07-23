"""
Scraper de Fybeca. El sitio migró de VTEX a Salesforce Commerce Cloud
(Demandware); la API vieja de VTEX ya no existe (por eso el scraper
anterior no traía nada). No hay una API JSON de catálogo pública, pero el
listado de categoría pagina vía el endpoint HTML "Search-UpdateGrid", que
responde directo a requests (sin sesión ni JS) -- no hace falta Playwright
en absoluto, se parsea el HTML con BeautifulSoup.
"""

import time
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from apps.comercios.models import Comercio
from apps.catalogo.models import Categoria, Producto
from apps.catalogo.utils import (
    comparten_palabra_clave,
    detectar_marca,
    extraer_cantidad_normalizada,
    extraer_conteo_normalizado,
    extraer_dosis_normalizada,
    normalizar_nombre,
)
from apps.precios.models import Precio

URL_BASE = "https://www.fybeca.com"
GRID_URL = f"{URL_BASE}/on/demandware.store/Sites-FybecaEcuador-Site/es_EC/Search-UpdateGrid"

# Mismos nombres de categoría que ya usa Cruz Azul (la otra farmacia), para
# maximizar la posibilidad de overlap real entre las 2.
CATEGORIAS_OBJETIVO = [
    ("dolor_y_fiebre", "Dolor y Fiebre"),
    ("vitaminas_y_minerales", "Vitaminas y Suplementos"),
    # Gripe y Tos: Fybeca no tiene un cgid propio para "gripe/tos/resfrio"
    # (se probaron varias variantes contra el sitio real y ninguna existe),
    # así que se usa "respiratorio" -- el bucket de Medicinas más cercano.
    # Es más ancho que el de Cruz Azul (incluye alergias/asma, ej. Zyrtec,
    # Seretide), así que se espera menor tasa de match que en Dolor y Fiebre.
    ("respiratorio", "Gripe y Tos"),
]

PRODUCTOS_POR_PAGINA = 18
MAX_PRODUCTOS = 300


class Command(BaseCommand):
    help = "Scrapea productos y precios de Fybeca hacia la base de datos de Kache"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre="Fybeca",
            tipo=Comercio.TIPO_FARMACIA,
            defaults={"sitio_web": URL_BASE},
        )

        for cgid, nombre_categoria in CATEGORIAS_OBJETIVO:
            self.stdout.write(f"Scrapeando: {nombre_categoria}")
            items = self._obtener_productos(cgid)
            self.stdout.write(f"  Encontrados {len(items)} productos")
            if not items:
                continue

            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
            creados, actualizados = 0, 0

            for item in items:
                nombre_normalizado = normalizar_nombre(item["nombre"])
                producto = Producto.objects.filter(nombre_normalizado=nombre_normalizado).first()
                if producto is None:
                    marca = detectar_marca(nombre_normalizado)
                    if marca:
                        # Farmacia: dosis (mg/gr) + conteo de unidades (x24,
                        # C/50) deben coincidir EXACTO los dos -- una fusión
                        # incorrecta acá es más delicada que en aceites/pinturas,
                        # así que si falta cualquiera de los dos no se fusiona
                        # por este camino (mejor falso negativo que falso positivo).
                        dosis = extraer_dosis_normalizada(item["nombre"])
                        conteo = extraer_conteo_normalizado(item["nombre"])
                        if dosis and conteo:
                            producto = Producto.objects.filter(
                                marca_normalizada=marca,
                                dosis_normalizada=dosis,
                                conteo_normalizado=conteo,
                            ).exclude(precios__comercio=comercio).first()
                        if producto is None:
                            # Solo puentea ENTRE comercios distintos: si Fybeca ya
                            # tiene su propio Precio en esta marca+cantidad, son
                            # dos items distintos de su propio catálogo.
                            cantidad = extraer_cantidad_normalizada(item["nombre"])
                            if cantidad:
                                # Marca+cantidad solas no distinguen líneas de producto
                                # distintas (ej. una pintura "para canchas" vs un esmalte
                                # estándar, misma marca y presentación) -- se exige además
                                # que compartan alguna palabra más allá de marca/unidad.
                                candidatos = Producto.objects.filter(
                                    marca_normalizada=marca, cantidad_normalizada=cantidad
                                ).exclude(precios__comercio=comercio)
                                producto = next(
                                    (c for c in candidatos if comparten_palabra_clave(
                                        nombre_normalizado, c.nombre_normalizado, marca
                                    )),
                                    None,
                                )
                if producto is None:
                    producto = Producto.objects.create(
                        nombre=item["nombre"],
                        categoria=categoria,
                        marca=item.get("marca", ""),
                        unidad_medida="unidad",
                        imagen_url=item.get("imagen_url"),
                    )
                _, fue_creado = Precio.objects.update_or_create(
                    producto=producto,
                    comercio=comercio,
                    defaults={"precio_actual": item["precio"]},
                )
                creados += 1 if fue_creado else 0
                actualizados += 0 if fue_creado else 1

            self.stdout.write(
                self.style.SUCCESS(f"  {creados} nuevos, {actualizados} actualizados")
            )

        self.stdout.write(self.style.SUCCESS("Listo."))

    def _obtener_productos(self, cgid):
        items = []
        pagina = 0

        while len(items) < MAX_PRODUCTOS:
            url = f"{GRID_URL}?cgid={cgid}&start={pagina * PRODUCTOS_POR_PAGINA}&sz={PRODUCTOS_POR_PAGINA}"
            try:
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                tiles = soup.select("div.product-tile")
                if not tiles:
                    break

                for tile in tiles:
                    nombre_el = tile.select_one(".pdp-link a.link")
                    precio_el = tile.select_one(".price .value")
                    marca_el = tile.select_one(".product-brand")
                    img_el = tile.select_one(".tile-image")

                    if not nombre_el or not precio_el:
                        continue

                    nombre = nombre_el.get_text(strip=True)
                    precio_attr = precio_el.get("content")
                    if not precio_attr:
                        continue
                    try:
                        precio_valor = Decimal(precio_attr).quantize(Decimal("0.01"))
                    except InvalidOperation:
                        continue
                    if precio_valor <= 0:
                        continue

                    marca = marca_el.get_text(strip=True) if marca_el else ""
                    imagen_url = img_el.get("src") if img_el else None
                    if imagen_url and imagen_url.startswith("/"):
                        imagen_url = URL_BASE + imagen_url

                    items.append({
                        "nombre": nombre,
                        "marca": marca,
                        "precio": precio_valor,
                        "imagen_url": imagen_url,
                    })

                if len(tiles) < PRODUCTOS_POR_PAGINA:
                    break
                pagina += 1
                time.sleep(0.3)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error: {e}"))
                break

        return items
