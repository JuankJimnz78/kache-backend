"""
Scraper de Fybeca Ecuador usando la API pública de VTEX.
"""

import time
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand

from apps.comercios.models import Comercio
from apps.catalogo.models import Categoria, Producto
from apps.precios.models import Precio

URL_BASE = "https://www.fybeca.com"
API_SEARCH = f"{URL_BASE}/_v/segment/graphql/v1"

# URLs reales encontradas en el sitio
CATEGORIAS_OBJETIVO = [
    ("vitaminas-adultos", "Vitaminas y Suplementos"),
    ("nutricion-y-vitaminas/suplementos-y-complementos", "Vitaminas y Suplementos"),
]

MAX_PRODUCTOS = 200
PRODUCTOS_POR_PAGINA = 50


class Command(BaseCommand):
    help = "Scrapea productos y precios de Fybeca Ecuador"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre="Fybeca",
            tipo=Comercio.TIPO_FARMACIA,
            defaults={"sitio_web": URL_BASE},
        )

        for slug, nombre_categoria in CATEGORIAS_OBJETIVO:
            self.stdout.write(f"Scrapeando: {slug}")
            items = self._obtener_productos_api(slug)

            if not items:
                self.stdout.write(self.style.WARNING(f"  Sin productos via API, intentando Playwright..."))
                items = self._obtener_productos_playwright(slug)

            self.stdout.write(f"  Encontrados {len(items)} productos")

            if not items:
                continue

            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
            creados, actualizados = 0, 0

            for item in items:
                producto, creado_ahora = Producto.objects.get_or_create(
                    nombre=item["nombre"],
                    defaults={
                        "categoria": categoria,
                        "marca": item.get("marca", ""),
                        "unidad_medida": "unidad",
                        "imagen_url": item.get("imagen_url"),
                    },
                )
                if not creado_ahora and not producto.imagen_url and item.get("imagen_url"):
                    producto.imagen_url = item["imagen_url"]
                    producto.save(update_fields=["imagen_url"])

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

    def _obtener_productos_api(self, slug):
        """Intenta la API de búsqueda de VTEX."""
        items = []
        page = 0

        while len(items) < MAX_PRODUCTOS:
            url = (
                f"{URL_BASE}/api/catalog_system/pub/products/search"
                f"?fq=c:{slug}&_from={page * PRODUCTOS_POR_PAGINA}"
                f"&_to={(page + 1) * PRODUCTOS_POR_PAGINA - 1}"
            )
            try:
                resp = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                if resp.status_code != 200:
                    break
                productos = resp.json()
                if not productos:
                    break

                for p in productos:
                    nombre = p.get("productName", "").strip()
                    marca = p.get("brand", "").strip()
                    skus = p.get("items", [])
                    if not nombre or not skus:
                        continue

                    imagen_url = None
                    imagenes = skus[0].get("images", [])
                    if imagenes:
                        imagen_url = imagenes[0].get("imageUrl")

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
                                    })
                                except InvalidOperation:
                                    pass
                                break
                        else:
                            continue
                        break

                if len(productos) < PRODUCTOS_POR_PAGINA:
                    break
                page += 1
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  API error: {e}"))
                break

        return items

    def _obtener_productos_playwright(self, slug):
        """Fallback con Playwright si la API no funciona."""
        import re
        from playwright.sync_api import sync_playwright

        items = []
        url = f"{URL_BASE}/{slug}/"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(6000)

                # Fybeca usa VTEX IO — buscar tarjetas de producto
                productos_el = page.query_selector_all("[class*='productSummary'], [class*='product-summary'], article")
                self.stdout.write(f"  Playwright encontró {len(productos_el)} elementos")

                for el in productos_el:
                    try:
                        nombre_el = el.query_selector("h3, h2, [class*='productName'], [class*='product-name']")
                        precio_el = el.query_selector("[class*='sellingPrice'], [class*='selling-price'], [class*='price']")
                        img_el = el.query_selector("img")

                        if not nombre_el or not precio_el:
                            continue

                        nombre = nombre_el.inner_text().strip()
                        precio_texto = precio_el.inner_text().strip()
                        imagen_url = img_el.get_attribute("src") if img_el else None

                        match = re.search(r"[\d\.]+", precio_texto.replace(",", "."))
                        if not match:
                            continue

                        precio = Decimal(match.group()).quantize(Decimal("0.01"))
                        if precio > 0 and nombre:
                            items.append({
                                "nombre": nombre,
                                "precio": precio,
                                "imagen_url": imagen_url,
                            })
                    except Exception:
                        continue

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Playwright error: {e}"))
            finally:
                browser.close()

        return items