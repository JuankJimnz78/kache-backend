"""
Reporta (sin modificar nada) productos que YA quedaron fusionados con más
de un Precio de distintos comercios, ordenados por qué tan distinta es la
diferencia de precio entre comercios. Una diferencia grande es señal de
posible falso positivo del matching (dos productos físicamente distintos
que terminaron bajo la misma fila de Producto), no prueba definitiva —
hay que revisar caso por caso.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.catalogo.models import Producto

UMBRAL_SOSPECHOSO = 0.20  # 20% de diferencia entre el precio más bajo y el más alto


class Command(BaseCommand):
    help = "Reporta productos ya fusionados con precios muy distintos entre comercios (posibles falsos positivos del matching)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--umbral", type=float, default=UMBRAL_SOSPECHOSO,
            help=f"Diferencia relativa mínima para marcar como sospechoso (default {UMBRAL_SOSPECHOSO})",
        )
        parser.add_argument(
            "--output", type=str, default=None,
            help="Ruta de archivo de texto donde además guardar el reporte completo",
        )

    def handle(self, *args, **options):
        umbral = options["umbral"]

        productos = (
            Producto.objects.annotate(n=Count("precios"))
            .filter(n__gt=1)
            .prefetch_related("precios__comercio")
        )

        filas = []
        for p in productos:
            precios = list(p.precios.select_related("comercio").all())
            valores = [precio.precio_actual for precio in precios]
            minimo, maximo = min(valores), max(valores)
            diferencia_relativa = float((maximo - minimo) / minimo) if minimo else 0.0
            filas.append((diferencia_relativa, p, precios))

        filas.sort(key=lambda x: -x[0])
        sospechosos = [f for f in filas if f[0] >= umbral]

        lineas = []
        lineas.append(f"Total de Producto con 2+ Precio: {len(filas)}")
        lineas.append(f"Umbral de diferencia relativa considerado sospechoso: {umbral:.0%}")
        lineas.append(f"Casos por encima del umbral: {len(sospechosos)}")
        lineas.append("")
        lineas.append("=== Todos los productos fusionados, ordenados de mayor a menor diferencia ===")
        lineas.append("")

        for diferencia_relativa, p, precios in filas:
            marca_bandera = " ** SOSPECHOSO **" if diferencia_relativa >= umbral else ""
            lineas.append(
                f"id={p.id} | {p.nombre!r} | marca={p.marca_normalizada!r} | "
                f"cantidad={p.cantidad_normalizada!r} | diferencia={diferencia_relativa:.0%}{marca_bandera}"
            )
            for precio in sorted(precios, key=lambda pr: pr.precio_actual):
                lineas.append(f"    {precio.comercio.nombre}: ${precio.precio_actual}")
            lineas.append("")

        reporte = "\n".join(lineas)
        self.stdout.write(reporte)

        ruta_salida = options.get("output")
        if ruta_salida:
            with open(ruta_salida, "w", encoding="utf-8") as f:
                f.write(reporte)
            self.stdout.write(self.style.SUCCESS(f"\nReporte también guardado en: {ruta_salida}"))
