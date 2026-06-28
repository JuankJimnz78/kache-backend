"""
Scraper de Supermaxi usando Playwright. Los precios se cargan con JavaScript,
así que no existen en el HTML estático y necesitamos un navegador real.

Uso:
    uv run manage.py scrapear_supermaxi

Qué hace:
  - Por cada entrada en SUCURSALES: registra Ciudad y Sucursal en la BD,
    selecciona ese local en la web y scrapea las categorías declaradas.
  - Los precios se guardan a nivel de Comercio (no Sucursal), porque ese es
    el dato que Kache compara entre cadenas.

Para agregar más sucursales: añade un dict más a SUCURSALES. La lógica de
scraping se ejecuta una vez por entrada.
"""

import re
import time
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright

from apps.comercios.models import Ciudad, Comercio, Sucursal
from apps.catalogo.models import Categoria, Producto
from apps.precios.models import Precio

URL_BASE = "https://www.supermaxi.com"
USER_AGENT = "KacheBot/1.0 (proyecto academico; contacto@ejemplo.edu)"
DELAY_ENTRE_PAGINAS = 3.0  # segundos entre navegaciones

# ── Configuración declarativa de sucursales ─────────────────────
# Cada entrada representa un local físico que el scraper selecciona
# antes de recoger precios. Agrega más dicts aquí para cubrir
# otras sucursales sin tocar la lógica de scraping.
SUCURSALES = [
    {
        "comercio":        "Supermaxi",
        "nombre_sucursal": "Supermaxi Iñaquito",
        "ciudad":          "Quito",
        "provincia":       "Pichincha",
        "direccion":       "Av. de los Shyris N35-174 y Av. Naciones Unidas",
        "selector_local":  "Supermaxi Iñaquito",  # texto del <option> en el <select>
    },
]

CATEGORIAS_OBJETIVO = [
    ("https://www.supermaxi.com/product-category/super-ofertas/", "Ofertas"),
    ("https://www.supermaxi.com/product-category/leches-y-sustitutos-lacteos/", "Leches"),
]


class Command(BaseCommand):
    help = "Scrapea productos y precios de Supermaxi hacia la base de datos de Kache"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre=SUCURSALES[0]["comercio"],
            tipo=Comercio.TIPO_SUPERMERCADO,
            defaults={"sitio_web": URL_BASE},
        )

        # Registrar sucursales configuradas (sin necesidad de scrapear el HTML)
        for cfg in SUCURSALES:
            ciudad, _ = Ciudad.objects.get_or_create(
                nombre=cfg["ciudad"],
                provincia=cfg["provincia"],
            )
            Sucursal.objects.get_or_create(
                comercio=comercio,
                nombre_sucursal=cfg["nombre_sucursal"],
                defaults={
                    "ciudad": ciudad,
                    "direccion": cfg["direccion"],
                    "activo": True,
                },
            )
            self.stdout.write(f"Sucursal registrada: {cfg['nombre_sucursal']} ({cfg['ciudad']})")

        # Scrapear precios por cada sucursal configurada
        for cfg in SUCURSALES:
            self.stdout.write(f"\n→ Scrapeando local: {cfg['nombre_sucursal']}")
            resultados = self._scrapear_local(cfg["selector_local"])
            self._guardar_precios(resultados, comercio)

        self.stdout.write(self.style.SUCCESS("\nListo."))

    def _scrapear_local(self, selector_local):
        """Abre el navegador, selecciona el local y recorre todas las categorías."""
        resultados = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            self.stdout.write("  Abriendo Supermaxi...")
            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=60000)
            time.sleep(DELAY_ENTRE_PAGINAS)

            self._seleccionar_local(page, selector_local)

            for url_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
                self.stdout.write(f"  Scrapeando categoría: {nombre_categoria}")
                resultados[nombre_categoria] = self._scrapear_categoria(page, url_categoria)
                time.sleep(DELAY_ENTRE_PAGINAS)

            browser.close()

        return resultados

    def _seleccionar_local(self, page, selector_local):
        try:
            selects = page.query_selector_all("select")
            seleccionado = False

            for sel in selects:
                opciones = sel.query_selector_all("option")
                for opcion in opciones:
                    texto = (opcion.inner_text() or "").strip()
                    if selector_local in texto:
                        valor = opcion.get_attribute("value")
                        sel.evaluate(
                            """(el, val) => {
                                el.value = val;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                el.dispatchEvent(new Event('input',  { bubbles: true }));
                            }""",
                            valor,
                        )
                        seleccionado = True
                        self.stdout.write(f"  Local seleccionado: '{texto}'")
                        break
                if seleccionado:
                    break

            if not seleccionado:
                self.stdout.write(self.style.WARNING(f"  No se encontró la opción '{selector_local}'."))
            time.sleep(DELAY_ENTRE_PAGINAS)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error seleccionando local: {e}"))

    def _scrapear_categoria(self, page, url):
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(DELAY_ENTRE_PAGINAS)

        productos_el = page.query_selector_all("li.product")
        self.stdout.write(f"    Encontrados {len(productos_el)} productos")

        items = []
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

    def _guardar_precios(self, resultados, comercio):
        for nombre_categoria, items in resultados.items():
            if not items:
                continue
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
            creados, actualizados = 0, 0

            for item in items:
                producto = None
                if item.get("codigo_barras"):
                    producto = Producto.objects.filter(codigo_barras=item["codigo_barras"]).first()
                if producto is None:
                    producto, _ = Producto.objects.get_or_create(
                        nombre=item["nombre"],
                        defaults={
                            "categoria": categoria,
                            "unidad_medida": "unidad",
                            "codigo_barras": item.get("codigo_barras"),
                        },
                    )
                _, fue_creado = Precio.objects.update_or_create(
                    producto=producto,
                    comercio=comercio,
                    defaults={"precio_actual": item["precio"]},
                )
                creados    += 1 if fue_creado else 0
                actualizados += 0 if fue_creado else 1

            self.stdout.write(
                f"    {nombre_categoria}: {creados} precios nuevos, {actualizados} actualizados"
            )

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

        try:
            return Decimal(numero)
        except InvalidOperation:
            return None
