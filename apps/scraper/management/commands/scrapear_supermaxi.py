"""
Scraper de Supermaxi usando Playwright. Los precios se cargan con JavaScript,
así que no existen en el HTML estático y necesitamos un navegador real.
"""

import re
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

URL_BASE = "https://www.supermaxi.com"
NOMBRE_LOCAL_DEFAULT = "Supermaxi Iñaquito"

# Aceites y Arroz: verificadas contra el sitio real, ambas se cruzan con
# marcas nacionales que también vende Coral (La Favorita, Banquete, Real).
# Leches: "Leches y Sustitutos" (padre de Enteras/Descremadas/Deslactosadas/
# etc., 383 productos) verificada contra el sitio real -- es el equivalente
# más cercano a como Coral mezcla todo eso en una sola categoría "Leches".
CATEGORIAS_OBJETIVO = [
    ("https://www.supermaxi.com/product-category/aceites-y-grasas-alacena/", "Aceites"),
    ("https://www.supermaxi.com/product-category/arroz-alacena/", "Arroz"),
    ("https://www.supermaxi.com/product-category/leches-y-sustitutos-lacteos/", "Leches"),
]

# Leches y Sustitutos tiene 383 productos (~12 páginas a 32 por página) frente
# a los ~50-100 de Aceites/Arroz -- se sube el techo para cubrirla completa.
# No afecta el tiempo de las categorías más chicas: el loop corta apenas una
# página llega vacía.
MAX_PAGINAS_POR_CATEGORIA = 12


class Command(BaseCommand):
    help = "Scrapea productos y precios de Supermaxi hacia la base de datos de Kache"

    def handle(self, *args, **options):
        resultados_por_categoria = self._scrapear_todo()

        comercio, _ = Comercio.objects.get_or_create(
            nombre="Supermaxi",
            tipo=Comercio.TIPO_SUPERMERCADO,
            defaults={"sitio_web": URL_BASE},
        )

        for nombre_categoria, items in resultados_por_categoria.items():
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

        self.stdout.write(self.style.SUCCESS("Listo."))

    def _scrapear_todo(self):
        resultados = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            self.stdout.write("Abriendo Supermaxi...")
            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            self._seleccionar_local(page)

            for url_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
                self.stdout.write(f"Scrapeando categoría: {nombre_categoria}")
                resultados[nombre_categoria] = self._scrapear_categoria(page, url_categoria)

            browser.close()

        return resultados

    def _seleccionar_local(self, page):
        try:
            selects = page.query_selector_all("select")
            seleccionado = False

            for sel in selects:
                opciones = sel.query_selector_all("option")
                for opcion in opciones:
                    texto = (opcion.inner_text() or "").strip()
                    if NOMBRE_LOCAL_DEFAULT in texto:
                        valor = opcion.get_attribute("value")
                        sel.evaluate(
                            """(el, val) => {
                                el.value = val;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                            }""",
                            valor,
                        )
                        seleccionado = True
                        self.stdout.write(f"  Local seleccionado: '{texto}' (value={valor})")
                        break
                if seleccionado:
                    break

            if not seleccionado:
                self.stdout.write(self.style.WARNING("  No se encontró la opción del local."))
            page.wait_for_timeout(3000)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error general seleccionando local: {e}"))

    def _scrapear_categoria(self, page, url):
        items = []
        for numero_pagina in range(1, MAX_PAGINAS_POR_CATEGORIA + 1):
            url_pagina = url if numero_pagina == 1 else f"{url}page/{numero_pagina}/"
            page.goto(url_pagina, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            productos_el = page.query_selector_all("li.product")
            if not productos_el:
                self.stdout.write(f"  Página {numero_pagina}: sin productos, fin de la categoría.")
                break
            self.stdout.write(f"  Página {numero_pagina}: {len(productos_el)} productos")

            for prod_el in productos_el:
                nombre_el = prod_el.query_selector(".woocommerce-loop-product__title")
                precio_el = prod_el.query_selector(".cf_api_regular_price")
                codigo_el = prod_el.query_selector(".cf_api_barcode")
                if not nombre_el or not precio_el:
                    continue

                nombre = nombre_el.inner_text().strip()
                precio_valor = self._limpiar_precio(precio_el.inner_text())
                if precio_valor is None:
                    continue

                codigo_barras = None
                if codigo_el:
                    match_codigo = re.search(r"\d+", codigo_el.inner_text())
                    if match_codigo:
                        codigo_barras = match_codigo.group()

                items.append({"nombre": nombre, "precio": precio_valor, "codigo_barras": codigo_barras})

        return items

    @staticmethod
    def _limpiar_precio(texto):
        """
        Convierte texto de precio a Decimal, detectando si el formato es
        USD ($3.92, punto = decimal) o latino (2.500,75, coma = decimal)
        según cuál símbolo aparece más a la derecha.
        """
        match = re.search(r"[\d.,]+", texto)
        if not match:
            return None
        numero = match.group()

        if "," in numero and "." in numero:
            if numero.rfind(",") > numero.rfind("."):
                numero = numero.replace(".", "").replace(",", ".")
            else:
                numero = numero.replace(",", "")
        elif "," in numero:
            partes = numero.split(",")
            if len(partes[-1]) == 2:
                numero = numero.replace(",", ".")
            else:
                numero = numero.replace(",", "")
        # Si solo hay puntos (o ningún símbolo), se asume formato USD tal cual.

        try:
            return Decimal(numero)
        except InvalidOperation:
            return None