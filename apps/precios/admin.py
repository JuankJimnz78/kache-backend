from django.contrib import admin
from .models import Precio, HistorialPrecio


@admin.register(Precio)
class PrecioAdmin(admin.ModelAdmin):
    list_display = ["id", "producto", "comercio", "precio_actual", "en_oferta", "precio_oferta", "fecha_actualizacion"]
    list_filter = ["comercio", "en_oferta"]
    search_fields = ["producto__nombre", "comercio__nombre"]


@admin.register(HistorialPrecio)
class HistorialPrecioAdmin(admin.ModelAdmin):
    list_display = ["id", "producto", "comercio", "precio_registrado", "fecha_registro"]
    list_filter = ["comercio"]
    search_fields = ["producto__nombre"]
    readonly_fields = ["producto", "comercio", "precio_registrado", "fecha_registro"]