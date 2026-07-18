"""
Scraper de Ferrisariato. ferrisariato.com es solo un sitio corporativo (sin
catálogo propio, protegido por Incapsula); su tienda real vive en
frecuento.com, el marketplace del grupo Corporación El Rosado (mismo grupo
que Coral, pero con una plataforma propia distinta a Magento). La API en
app.frecuento.com es JSON público sin login, así que no hace falta Playwright.
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

URL_BASE = "https://www.frecuento.com"
API_BASE = "https://app.frecuento.com"

# Pinturas: verificada contra el sitio real, se cruza con la marca nacional
# Pinturas Unidas (y Pintuco) que también vende Kywi.
CATEGORIAS_OBJETIVO = [
    (18300, "Pinturas"),
]

MAX_PAGINAS_POR_CATEGORIA = 5


class Command(BaseCommand):
    help = "Scrapea productos y precios de Ferrisariato (vía frecuento.com) hacia la base de datos de Kache"

    def handle(self, *args, **options):
        comercio, _ = Comercio.objects.get_or_create(
            nombre="Ferrisariato",
            tipo=Comercio.TIPO_FERRETERIA,
            defaults={"sitio_web": URL_BASE},
        )

        for id_categoria, nombre_categoria in CATEGORIAS_OBJETIVO:
            self.stdout.write(f"Scrapeando: {nombre_categoria}")
            items = self._obtener_productos(id_categoria)
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

    def _obtener_productos(self, id_categoria):
        # No trae codigo_barras: la API de Frecuento no expone EAN/GTIN,
        # solo un "code" interno de SKU (ver diagnóstico previo a implementar).
        items = []

        for pagina in range(1, MAX_PAGINAS_POR_CATEGORIA + 1):
            url = f"{API_BASE}/products/?category={id_categoria}&page={pagina}"
            try:
                resp = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                if resp.status_code != 200:
                    break
                data = resp.json()
                resultados = data.get("results", [])
                if not resultados:
                    break

                for p in resultados:
                    nombre = (p.get("name") or "").strip()
                    if not nombre or not p.get("has_stock"):
                        continue

                    precio_raw = p.get("amount_total")
                    if not precio_raw:
                        continue
                    try:
                        precio = Decimal(str(precio_raw)).quantize(Decimal("0.01"))
                    except InvalidOperation:
                        continue

                    fotos = p.get("photos") or []
                    imagen_url = fotos[0] if fotos else None

                    items.append({
                        "nombre": nombre,
                        "marca": (p.get("brand") or "").strip(),
                        "precio": precio,
                        "imagen_url": imagen_url,
                    })

                if pagina >= data.get("pages", pagina):
                    break
                time.sleep(0.3)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Error: {e}"))
                break

        return items
