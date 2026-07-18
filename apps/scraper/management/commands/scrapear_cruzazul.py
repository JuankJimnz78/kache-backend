"""
Scraper de Farmacias Cruz Azul usando la API pública de VTEX (a diferencia
de Fybeca, que migró de plataforma, este sitio sigue siendo VTEX real y la
API legacy de búsqueda responde con datos vigentes).
"""

import time
from decimal import Decimal, InvalidOperation

import requests
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

URL_BASE = "https://www.farmaciascruzazul.ec"

# Categorías de alta rotación (no de nicho), verificadas contra el árbol de
# categorías real del sitio antes de usarlas.
CATEGORIAS_OBJETIVO = [
    ("tratamientos-y-salud/alivio-del-dolor/dolor-y-fiebre-de-adultos", "Dolor y Fiebre"),
    ("vitaminas-y-suplementos", "Vitaminas y Suplementos"),
]

PRODUCTOS_POR_PAGINA = 50
MAX_PRODUCTOS = 300


class Command(BaseCommand):
    help = "Scrapea productos y precios de Farmacias Cruz Azul hacia la base de datos de Kache"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre="Cruz Azul",
            tipo=Comercio.TIPO_FARMACIA,
            defaults={"sitio_web": URL_BASE},
        )

        for slug_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
            self.stdout.write(f"Scrapeando: {nombre_categoria}")
            items = self._obtener_productos(slug_categoria)
            self.stdout.write(f"  Encontrados {len(items)} productos")
            if not items:
                continue

            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
            creados, actualizados = 0, 0

            for item in items:
                nombre_normalizado = normalizar_nombre(item["nombre"])
                producto = None
                if item.get("codigo_barras"):
                    producto = Producto.objects.filter(codigo_barras=item["codigo_barras"]).first()
                if producto is None:
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
                            # Solo sirve para puentear ENTRE comercios distintos: si
                            # este comercio ya tiene un Precio propio en la misma
                            # marca+cantidad, son dos items distintos de su propio
                            # catálogo y no deben fusionarse solo por compartir esa clave.
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
                        codigo_barras=item.get("codigo_barras"),
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

    def _obtener_productos(self, slug_categoria):
        items = []
        pagina = 0

        while len(items) < MAX_PRODUCTOS:
            url = (
                f"{URL_BASE}/api/catalog_system/pub/products/search/{slug_categoria}"
                f"?_from={pagina * PRODUCTOS_POR_PAGINA}&_to={(pagina + 1) * PRODUCTOS_POR_PAGINA - 1}"
            )
            try:
                resp = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                if resp.status_code not in (200, 206):
                    break
                productos = resp.json()
                if not productos or not isinstance(productos, list):
                    break

                for p in productos:
                    nombre = (p.get("productName") or "").strip()
                    marca = (p.get("brand") or "").strip()
                    skus = p.get("items", [])
                    if not nombre or not skus:
                        continue

                    imagen_url = None
                    imagenes = skus[0].get("images", [])
                    if imagenes:
                        imagen_url = imagenes[0].get("imageUrl")

                    codigo_barras = None
                    for sku in skus:
                        ean = (sku.get("ean") or "").strip()
                        if ean:
                            codigo_barras = ean
                            break

                    for sku in skus:
                        for seller in sku.get("sellers", []):
                            oferta = seller.get("commertialOffer", {})
                            precio_raw = oferta.get("Price", 0)
                            disponible = oferta.get("IsAvailable", False)
                            if disponible and precio_raw > 0:
                                try:
                                    precio = Decimal(str(precio_raw)).quantize(Decimal("0.01"))
                                    items.append({
                                        "nombre": nombre,
                                        "marca": marca,
                                        "precio": precio,
                                        "imagen_url": imagen_url,
                                        "codigo_barras": codigo_barras,
                                    })
                                except InvalidOperation:
                                    pass
                                break
                        else:
                            continue
                        break

                if len(productos) < PRODUCTOS_POR_PAGINA:
                    break
                pagina += 1
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error: {e}"))
                break

        return items
