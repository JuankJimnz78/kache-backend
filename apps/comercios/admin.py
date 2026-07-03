from django.contrib import admin
from .models import Comercio, Sucursal


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "tipo", "activo", "destacado", "logo_url"]
    fields = ["nombre", "tipo", "logo_url", "sitio_web", "activo", "destacado", "fecha_fin_destacado"]
    list_filter = ["tipo", "activo", "destacado"]
    search_fields = ["nombre"]


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre_sucursal", "comercio", "ciudad", "activo"]
    list_filter = ["comercio", "ciudad", "activo"]
    search_fields = ["nombre_sucursal", "ciudad", "direccion"]