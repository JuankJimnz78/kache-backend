"""
Reporta (sin modificar nada) grupos de Producto que deberían ser el mismo
producto físico, aplicando retroactivamente a filas ya guardadas el mismo
criterio de matching que ya usan los scrapers al crear productos nuevos:
codigo_barras > nombre_normalizado > marca_normalizada + cantidad_normalizada.

Dos filas quedan en el mismo grupo si coinciden en CUALQUIERA de esos tres
niveles (unión transitiva tipo union-find), igual que si el scraper las
hubiera comparado una contra otra en el momento de crearlas.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.catalogo.models import Producto


class _UnionFind:
    def __init__(self):
        self.padre = {}

    def find(self, x):
        self.padre.setdefault(x, x)
        while self.padre[x] != x:
            self.padre[x] = self.padre[self.padre[x]]
            x = self.padre[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.padre[ra] = rb


class Command(BaseCommand):
    help = "Reporta grupos de Producto duplicados según codigo_barras/nombre_normalizado/marca+cantidad. No modifica la base de datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", type=str, default=None,
            help="Ruta de archivo de texto donde además guardar el reporte completo",
        )

    def handle(self, *args, **options):
        productos = list(
            Producto.objects.all().only(
                "id", "nombre", "codigo_barras", "nombre_normalizado",
                "marca_normalizada", "cantidad_normalizada", "creado_en",
            )
        )

        uf = _UnionFind()
        for p in productos:
            uf.find(p.id)

        def agrupar_por(func_clave):
            grupos = defaultdict(list)
            for p in productos:
                clave = func_clave(p)
                if clave:
                    grupos[clave].append(p.id)
            for ids in grupos.values():
                if len(ids) > 1:
                    primero = ids[0]
                    for otro in ids[1:]:
                        uf.union(primero, otro)

        # Mismos 3 niveles y mismo orden de prioridad que usan los scrapers
        # (apps/catalogo/utils.py), pero aquí se aplican los 3 como unión
        # transitiva en vez de "primero que matchea gana", porque estamos
        # agrupando filas que ya existen, no decidiendo si crear una nueva.
        agrupar_por(lambda p: p.codigo_barras if p.codigo_barras else None)
        agrupar_por(lambda p: p.nombre_normalizado if p.nombre_normalizado else None)
        agrupar_por(
            lambda p: (p.marca_normalizada, p.cantidad_normalizada)
            if p.marca_normalizada and p.cantidad_normalizada else None
        )

        grupos_finales = defaultdict(list)
        for p in productos:
            grupos_finales[uf.find(p.id)].append(p)

        grupos_reales = [g for g in grupos_finales.values() if len(g) > 1]
        grupos_reales.sort(key=lambda g: -len(g))

        # Conteo total actual (línea base para comparar antes/después de la
        # fusión real en el PASO 3, cuando se apruebe).
        total_precio = sum(p.precios.count() for p in productos)
        total_favorito = sum(p.favorito_set.count() for p in productos)
        total_item_comparacion = sum(p.itemcomparacion_set.count() for p in productos)
        total_alerta = sum(p.alertaprecio_set.count() for p in productos)
        total_reporte = sum(p.reporteproducto_set.count() for p in productos)
        total_historial = sum(p.historial_precios.count() for p in productos)

        lineas = []
        lineas.append(f"Total de Producto analizados: {len(productos)}")
        lineas.append(f"Grupos de duplicados encontrados: {len(grupos_reales)}")
        total_filas_en_grupos = sum(len(g) for g in grupos_reales)
        lineas.append(f"Filas de Producto involucradas: {total_filas_en_grupos}")
        lineas.append(f"Filas que se eliminarían si se fusiona todo: {total_filas_en_grupos - len(grupos_reales)}")
        lineas.append("")
        lineas.append("Conteo total actual (línea base para comparar antes/después de fusionar):")
        lineas.append(f"  Precio={total_precio} Favorito={total_favorito} ItemComparacion={total_item_comparacion} "
                       f"AlertaPrecio={total_alerta} ReporteProducto={total_reporte} HistorialPrecio={total_historial}")
        lineas.append("")

        for i, grupo in enumerate(grupos_reales, start=1):
            grupo = sorted(grupo, key=lambda p: p.creado_en)
            lineas.append(f"=== Grupo {i} ({len(grupo)} filas) ===")

            comercios_vistos = defaultdict(list)  # comercio_nombre -> [(producto_id, precio, fecha)]
            for p in grupo:
                n_precios = p.precios.count()
                n_favoritos = p.favorito_set.count()
                n_items_comparacion = p.itemcomparacion_set.count()
                n_alertas = p.alertaprecio_set.count()
                n_reportes = p.reporteproducto_set.count()
                n_historial = p.historial_precios.count()

                lineas.append(
                    f"  id={p.id} | nombre={p.nombre!r} | marca={p.marca_normalizada!r} | "
                    f"cantidad={p.cantidad_normalizada!r} | codigo_barras={p.codigo_barras!r} | "
                    f"creado_en={p.creado_en:%Y-%m-%d %H:%M} | "
                    f"Precio={n_precios} Favorito={n_favoritos} ItemComparacion={n_items_comparacion} "
                    f"AlertaPrecio={n_alertas} ReporteProducto={n_reportes} HistorialPrecio={n_historial}"
                )
                for precio in p.precios.select_related("comercio"):
                    comercios_vistos[precio.comercio.nombre].append(
                        (p.id, precio.precio_actual, precio.fecha_actualizacion)
                    )

            conflictos = {c: filas for c, filas in comercios_vistos.items() if len(filas) > 1}
            if conflictos:
                lineas.append("  ** CONFLICTO: más de un Precio del mismo comercio en este grupo **")
                for comercio_nombre, filas in conflictos.items():
                    detalle = ", ".join(
                        f"producto_id={pid} precio={precio} actualizado={fecha:%Y-%m-%d}"
                        for pid, precio, fecha in filas
                    )
                    lineas.append(f"    {comercio_nombre}: {detalle}")

            lineas.append("")

        reporte = "\n".join(lineas)
        self.stdout.write(reporte)

        ruta_salida = options.get("output")
        if ruta_salida:
            with open(ruta_salida, "w", encoding="utf-8") as f:
                f.write(reporte)
            self.stdout.write(self.style.SUCCESS(f"\nReporte también guardado en: {ruta_salida}"))
