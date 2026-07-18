"""
Scraper de Coral Hipermercados usando Playwright.
Soporta dos modos: por categoría (con paginación) y por URL de producto
específica (para garantizar que un producto puntual quede capturado,
sin depender de en qué página de la categoría aparezca).
"""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright

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

URL_BASE = "https://coralhipermercados.com/"
NOMBRE_TIENDA_DEFAULT = "Calderon - Quito"

# Aceites y Arroz: verificadas contra el sitio real, ambas se cruzan con
# marcas nacionales que también vende Supermaxi (La Favorita, Banquete, Real).
CATEGORIAS_OBJETIVO = [
    ("https://coralhipermercados.com/comisariato/condimentos-y-aderezos/aceites.html", "Aceites"),
    ("https://coralhipermercados.com/comisariato/alimentos-secos-y-despensa/arroz.html", "Arroz"),
]

# Productos puntuales que queremos garantizar, con su categoría destino.
PRODUCTOS_DIRECTOS = [
    ("https://coralhipermercados.com/leche-entera-parmalat-900ml-269.html", "Leches"),
]

MAX_PAGINAS_POR_CATEGORIA = 8


class Command(BaseCommand):
    help = "Scrapea productos y precios de Coral Hipermercados hacia la base de datos de Kache"

    def handle(self, *args, **options):
        resultados_por_categoria, resultados_directos = self._scrapear_todo()

        comercio, _ = Comercio.objects.get_or_create(
            nombre="Coral",
            tipo=Comercio.TIPO_SUPERMERCADO,
            defaults={"sitio_web": URL_BASE},
        )

        self._guardar(resultados_por_categoria, comercio)
        self._guardar(resultados_directos, comercio)

        self.stdout.write(self.style.SUCCESS("Listo."))

    def _guardar(self, resultados_por_categoria, comercio):
        for nombre_categoria, items in resultados_por_categoria.items():
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
                            # catálogo (ej. "Arroz Real" vs "Arroz Real Viejo") y no
                            # deben fusionarse solo por compartir esa clave.
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
                        unidad_medida="unidad",
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
                f"{nombre_categoria}: {creados} precios nuevos, {actualizados} actualizados"
            )

    def _scrapear_todo(self):
        resultados_categorias = {}
        resultados_directos = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            self.stdout.write("Abriendo Coral Hipermercados...")
            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            self._seleccionar_tienda(page)

            for url_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
                self.stdout.write(f"Scrapeando categoría: {nombre_categoria}")
                resultados_categorias[nombre_categoria] = self._scrapear_categoria_paginada(page, url_categoria)

            for url_producto, nombre_categoria in PRODUCTOS_DIRECTOS:
                self.stdout.write(f"Scrapeando producto directo: {url_producto}")
                item = self._scrapear_producto_directo(page, url_producto)
                if item:
                    resultados_directos.setdefault(nombre_categoria, []).append(item)

            browser.close()

        return resultados_categorias, resultados_directos

    def _seleccionar_tienda(self, page):
        try:
            li = page.query_selector(f"li.store-selector-item:has-text('{NOMBRE_TIENDA_DEFAULT}')")
            if not li:
                self.stdout.write(self.style.WARNING("  No se encontró el <li> de la tienda."))
                return
            li.click(force=True)
            page.wait_for_timeout(1000)
            try:
                page.click("text=Confirmar", timeout=3000, force=True)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            self.stdout.write(f"  Tienda seleccionada: {NOMBRE_TIENDA_DEFAULT}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error seleccionando tienda: {e}"))

    def _scrapear_categoria_paginada(self, page, url_base):
        items_totales = []
        for numero_pagina in range(1, MAX_PAGINAS_POR_CATEGORIA + 1):
            url = url_base if numero_pagina == 1 else f"{url_base}?p={numero_pagina}"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            productos_el = page.query_selector_all("li.product-item")
            if not productos_el:
                self.stdout.write(f"  Página {numero_pagina}: sin productos, fin de la categoría.")
                break
            self.stdout.write(f"  Página {numero_pagina}: {len(productos_el)} productos")
            for prod_el in productos_el:
                nombre_el = prod_el.query_selector(".product-item-link")
                precio_el = prod_el.query_selector('[data-price-type="finalPrice"]')
                if not nombre_el or not precio_el:
                    continue
                nombre = nombre_el.inner_text().strip()
                precio_attr = precio_el.get_attribute("data-price-amount")
                try:
                    precio_valor = Decimal(precio_attr).quantize(Decimal("0.01"))
                except (InvalidOperation, TypeError):
                    continue
                items_totales.append({"nombre": nombre, "precio": precio_valor})
        return items_totales

    def _scrapear_producto_directo(self, page, url):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            nombre_el = page.query_selector("h1.page-title span") or page.query_selector("h1.page-title")
            precio_el = page.query_selector('[data-price-type="finalPrice"]')

            if not nombre_el or not precio_el:
                self.stdout.write(self.style.WARNING(
                    f"  No se encontró nombre o precio en {url} — "
                    "puede que la estructura de la página de producto sea distinta a la del listado."
                ))
                # Diagnóstico: mostramos qué hay en pantalla para ajustar selectores si falla.
                titulo_html = page.content()[:500]
                self.stdout.write(f"  Primeros 500 caracteres de la página: {titulo_html}")
                return None

            nombre = nombre_el.inner_text().strip()
            precio_attr = precio_el.get_attribute("data-price-amount")
            precio_valor = Decimal(precio_attr).quantize(Decimal("0.01"))

            self.stdout.write(f"  Encontrado: '{nombre}' - {precio_valor}")
            return {"nombre": nombre, "precio": precio_valor}
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error scrapeando producto directo: {e}"))
            return None