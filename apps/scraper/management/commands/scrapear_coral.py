"""
Scraper de Coral Hipermercados usando Playwright.
Soporta dos modos: por categoría (con paginación) y por URL de producto
específica (para garantizar que un producto puntual quede capturado).

Uso:
    uv run manage.py scrapear_coral

Robots.txt de Coral (VERIFICADO — respetar siempre):
  - Disallow: /catalog/     → NO scrapear rutas bajo /catalog/
  - Disallow: /*?           → NO usar URLs con parámetros (?)
  - La paginación con ?p=N viola esta regla; solo se usa la primera página
    de cada categoría. Para más productos, añade URLs directas a
    PRODUCTOS_DIRECTOS o nuevas categorías permitidas a CATEGORIAS_OBJETIVO.

Qué hace:
  - Por cada entrada en SUCURSALES: registra Ciudad y Sucursal en la BD,
    selecciona ese local en la web y scrapea las categorías/productos.
  - Los precios se guardan a nivel de Comercio (no Sucursal).

Para agregar más sucursales: añade un dict más a SUCURSALES.
"""

import time
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright

from apps.comercios.models import Ciudad, Comercio, Sucursal
from apps.catalogo.models import Categoria, Producto
from apps.precios.models import Precio

URL_BASE = "https://coralhipermercados.com/"
USER_AGENT = "KacheBot/1.0 (proyecto academico; contacto@ejemplo.edu)"
DELAY_ENTRE_PAGINAS = 3.0  # segundos entre navegaciones

# ── Configuración declarativa de sucursales ─────────────────────
# Completa los campos marcados con COMPLETAR antes de ejecutar.
# selector_local es el texto del <li> que el scraper usa para
# hacer clic y seleccionar la tienda en la web de Coral.
SUCURSALES = [
    {
        "comercio":        "Coral",
        "nombre_sucursal": "COMPLETAR",          # ej. "Coral Calderón"
        "ciudad":          "COMPLETAR",          # ej. "Quito"
        "provincia":       "COMPLETAR",          # ej. "Pichincha"
        "direccion":       "COMPLETAR",          # ej. "Av. Geovanni Calles y Luis Tufiño"
        "selector_local":  "Calderon - Quito",   # texto del <li> en el selector de tiendas
    },
]

CATEGORIAS_OBJETIVO = [
    ("https://coralhipermercados.com/comisariato/lacteos-y-derivados/leches.html", "Leches"),
]

# Productos puntuales que queremos garantizar, con su categoría destino.
# Las URLs de página de producto (sin /catalog/ ni parámetros ?) están permitidas.
PRODUCTOS_DIRECTOS = [
    ("https://coralhipermercados.com/leche-entera-parmalat-900ml-269.html", "Leches"),
]


class Command(BaseCommand):
    help = "Scrapea productos y precios de Coral Hipermercados hacia la base de datos de Kache"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre=SUCURSALES[0]["comercio"],
            tipo=Comercio.TIPO_SUPERMERCADO,
            defaults={"sitio_web": URL_BASE},
        )

        # Registrar sucursales configuradas (sin extraer nada del HTML)
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
            self.stdout.write(f"\n→ Scrapeando local: {cfg['selector_local']}")
            resultados_cat, resultados_dir = self._scrapear_local(cfg["selector_local"])
            self._guardar_precios(resultados_cat, comercio)
            self._guardar_precios(resultados_dir, comercio)

        self.stdout.write(self.style.SUCCESS("\nListo."))

    def _scrapear_local(self, selector_local):
        """Abre el navegador, selecciona el local y recorre categorías y productos directos."""
        resultados_categorias = {}
        resultados_directos   = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page    = context.new_page()

            self.stdout.write("  Abriendo Coral Hipermercados...")
            page.goto(URL_BASE, wait_until="domcontentloaded", timeout=60000)
            time.sleep(DELAY_ENTRE_PAGINAS)

            self._seleccionar_tienda(page, selector_local)

            for url_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
                self.stdout.write(f"  Scrapeando categoría: {nombre_categoria}")
                # Solo primera página — páginas siguientes usan ?p=N (bloqueado por robots.txt)
                resultados_categorias[nombre_categoria] = self._scrapear_primera_pagina(page, url_categoria)
                time.sleep(DELAY_ENTRE_PAGINAS)

            for url_producto, nombre_categoria in PRODUCTOS_DIRECTOS:
                self.stdout.write(f"  Scrapeando producto directo: {url_producto}")
                item = self._scrapear_producto_directo(page, url_producto)
                if item:
                    resultados_directos.setdefault(nombre_categoria, []).append(item)
                time.sleep(DELAY_ENTRE_PAGINAS)

            browser.close()

        return resultados_categorias, resultados_directos

    def _seleccionar_tienda(self, page, selector_local):
        try:
            li = page.query_selector(f"li.store-selector-item:has-text('{selector_local}')")
            if not li:
                self.stdout.write(self.style.WARNING(f"  No se encontró el <li> para '{selector_local}'."))
                return
            li.click(force=True)
            time.sleep(1)
            try:
                page.click("text=Confirmar", timeout=3000, force=True)
            except Exception:
                pass
            time.sleep(DELAY_ENTRE_PAGINAS)
            self.stdout.write(f"  Tienda seleccionada: {selector_local}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error seleccionando tienda: {e}"))

    def _scrapear_primera_pagina(self, page, url):
        """
        Scrapea SOLO la primera página de la categoría.
        La paginación con ?p=N está bloqueada en el robots.txt de Coral
        (Disallow: /*?) y no se usa.
        """
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(DELAY_ENTRE_PAGINAS)

        productos_el = page.query_selector_all("li.product-item")
        self.stdout.write(f"    Encontrados {len(productos_el)} productos")

        items = []
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
            items.append({"nombre": nombre, "precio": precio_valor})

        return items

    def _scrapear_producto_directo(self, page, url):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(DELAY_ENTRE_PAGINAS)

            nombre_el = page.query_selector("h1.page-title span") or page.query_selector("h1.page-title")
            precio_el = page.query_selector('[data-price-type="finalPrice"]')

            if not nombre_el or not precio_el:
                self.stdout.write(self.style.WARNING(
                    f"  No se encontró nombre o precio en {url}"
                ))
                return None

            nombre      = nombre_el.inner_text().strip()
            precio_attr = precio_el.get_attribute("data-price-amount")
            precio_valor = Decimal(precio_attr).quantize(Decimal("0.01"))

            self.stdout.write(f"    Encontrado: '{nombre}' — {precio_valor}")
            return {"nombre": nombre, "precio": precio_valor}
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Error scrapeando producto directo: {e}"))
            return None

    def _guardar_precios(self, resultados, comercio):
        for nombre_categoria, items in resultados.items():
            if not items:
                continue
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
            creados, actualizados = 0, 0

            for item in items:
                producto, _ = Producto.objects.get_or_create(
                    nombre=item["nombre"],
                    defaults={"categoria": categoria, "unidad_medida": "unidad"},
                )
                _, fue_creado = Precio.objects.update_or_create(
                    producto=producto,
                    comercio=comercio,
                    defaults={"precio_actual": item["precio"]},
                )
                creados      += 1 if fue_creado else 0
                actualizados += 0 if fue_creado else 1

            self.stdout.write(
                f"    {nombre_categoria}: {creados} precios nuevos, {actualizados} actualizados"
            )
