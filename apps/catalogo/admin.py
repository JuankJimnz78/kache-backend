from django.contrib import admin
from django.contrib import messages
from django.db import IntegrityError

from .models import Marca, Etiqueta, Categoria, Producto


@admin.action(description="Fusionar productos seleccionados en uno solo")
def fusionar_productos(modeladmin, request, queryset):
    from apps.precios.models import Precio, HistorialPrecio
    from apps.extras.models import Favorito, AlertaPrecio, ReporteProducto
    from apps.comparador.models import ItemComparacion

    productos = list(queryset.order_by("id"))
    if len(productos) < 2:
        modeladmin.message_user(request, "Selecciona al menos 2 productos para fusionar.", level=messages.WARNING)
        return

    canonico = productos[0]
    duplicados = productos[1:]
    modelos_a_reasignar = [Precio, HistorialPrecio, Favorito, AlertaPrecio, ReporteProducto, ItemComparacion]

    for duplicado in duplicados:
        for Modelo in modelos_a_reasignar:
            for registro in Modelo.objects.filter(producto=duplicado):
                registro.producto = canonico
                try:
                    registro.save()
                except IntegrityError:
                    registro.delete()
        duplicado.delete()

    modeladmin.message_user(
        request,
        f"Se fusionaron {len(duplicados)} producto(s) en '{canonico.nombre}' (ID {canonico.id}).",
        level=messages.SUCCESS,
    )


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "pais_origen", "sitio_web"]
    search_fields = ["nombre", "pais_origen"]


@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "descripcion"]
    search_fields = ["nombre"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "categoria_padre"]
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "marca", "categoria", "comercios_con_precio", "codigo_barras"]
    list_filter = ["categoria", "marca"]
    search_fields = ["nombre", "marca__nombre", "codigo_barras"]
    filter_horizontal = ["etiquetas"]
    actions = [fusionar_productos]

    @admin.display(description="Comercios")
    def comercios_con_precio(self, obj):
        nombres = obj.precios.select_related("comercio").values_list("comercio__nombre", flat=True)
        return ", ".join(sorted(set(nombres))) or "(sin precio)"
