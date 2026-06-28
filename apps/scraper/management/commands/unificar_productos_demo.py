"""
Management command que unifica manualmente productos equivalentes entre
Supermaxi y Coral para la demo académica.

    uv run manage.py unificar_productos_demo

CÓMO USARLO
-----------
1. Corre ambos scrapers primero para poblar la BD.
2. Abre el admin (/admin/catalogo/producto/) y busca los pares equivalentes.
3. Rellena PARES_DEMO con (id_canonico_supermaxi, id_duplicado_coral).
4. Corre este command. Es IDEMPOTENTE: puedes repetirlo sin miedo.

QUÉ HACE POR CADA PAR
----------------------
- El Producto de Supermaxi (id_canonico) se CONSERVA tal cual.
- El Precio de Coral apuntado al duplicado se reasigna al canónico
  (update_or_create respeta unique_together [producto, comercio]).
- Cualquier FK de otros modelos (Favorito, Alerta, Reporte, ItemComparacion)
  que apuntara al duplicado se reasigna al canónico.
- El Producto duplicado de Coral se ELIMINA.

RESULTADO
---------
1 Producto canónico → 2 Precio (uno por Supermaxi, uno por Coral),
listo para que el endpoint /comparar/ los devuelva juntos.
"""

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from apps.catalogo.models import Producto
from apps.precios.models import Precio
from apps.extras.models import Favorito, AlertaPrecio, ReporteProducto
from apps.comparador.models import ItemComparacion

# ── Lista de pares a unificar ───────────────────────────────────
# Formato: (id_canonico_supermaxi, id_duplicado_coral)
# El canónico se CONSERVA; el duplicado se fusiona y se ELIMINA.
#
# Ejemplo real detectado:
#   (46, 67)  →  "Bebida De Leche Frutilla YOGU YOGU 200 Ml" (Supermaxi, cod. 7861226400547)
#                "BEBIDA DE LECHE FRUTILLA YOGU YOGU NESTL"  (Coral, cod. null)
#
# Añade más pares debajo. Consulta los IDs en el admin.
PARES_DEMO = [
    # (46, 67),
]

# Modelos con FK a Producto que hay que reasignar antes de borrar el duplicado
_MODELOS_FK_PRODUCTO = [Favorito, AlertaPrecio, ReporteProducto, ItemComparacion]


class Command(BaseCommand):
    help = "Unifica manualmente productos equivalentes entre comercios (demo académica)"

    def handle(self, *args, **options):
        if not PARES_DEMO:
            self.stdout.write(self.style.WARNING(
                "PARES_DEMO está vacío.\n"
                "Abre el admin en /admin/catalogo/producto/, identifica los IDs de\n"
                "productos equivalentes entre Supermaxi y Coral, y rellena la lista\n"
                "antes de volver a correr este command."
            ))
            return

        unificados = 0
        saltados   = 0

        for id_canonico, id_duplicado in PARES_DEMO:
            self.stdout.write(f"\n── Par ({id_canonico}, {id_duplicado}) ──")

            # Verificar que el canónico exista
            try:
                canonico = Producto.objects.get(pk=id_canonico)
            except Producto.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  Canónico id={id_canonico} no existe — saltando."
                ))
                saltados += 1
                continue

            # Verificar que el duplicado exista (si ya fue eliminado, es idempotente)
            try:
                duplicado = Producto.objects.get(pk=id_duplicado)
            except Producto.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  Duplicado id={id_duplicado} no existe (ya fue unificado) — saltando."
                ))
                saltados += 1
                continue

            self.stdout.write(f"  Canónico  [{id_canonico}]: {canonico.nombre}")
            self.stdout.write(f"  Duplicado [{id_duplicado}]: {duplicado.nombre}")

            # ── 1. Reasignar Precio(s) del duplicado al canónico ─
            for precio_dup in Precio.objects.filter(producto=duplicado):
                _, creado = Precio.objects.update_or_create(
                    producto=canonico,
                    comercio=precio_dup.comercio,
                    defaults={
                        "precio_actual": precio_dup.precio_actual,
                        "precio_oferta": precio_dup.precio_oferta,
                        "en_oferta":     precio_dup.en_oferta,
                    },
                )
                accion = "creado" if creado else "actualizado"
                self.stdout.write(
                    f"  Precio {accion}: {precio_dup.comercio.nombre} → "
                    f"${precio_dup.precio_actual}"
                )

            # ── 2. Reasignar FKs de otros modelos ────────────────
            for Modelo in _MODELOS_FK_PRODUCTO:
                registros = list(Modelo.objects.filter(producto=duplicado))
                for obj in registros:
                    obj.producto = canonico
                    try:
                        obj.save()
                    except IntegrityError:
                        # unique_together: ya existe un registro equivalente en el canónico
                        obj.delete()
                if registros:
                    self.stdout.write(
                        f"  {Modelo.__name__}: {len(registros)} registro(s) reasignado(s)."
                    )

            # ── 3. Eliminar el duplicado ──────────────────────────
            duplicado.delete()
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ Duplicado [{id_duplicado}] eliminado. "
                f"Canónico [{id_canonico}] conservado con todos sus precios."
            ))
            unificados += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nResumen: {unificados} par(es) unificado(s), {saltados} saltado(s)."
        ))
