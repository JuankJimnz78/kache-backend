from django.contrib import admin
from .models import Ciudad, Comercio, Sucursal


@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "provincia"]
    list_filter = ["provincia"]
    search_fields = ["nombre", "provincia"]


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "tipo", "activo", "destacado", "fecha_fin_destacado"]
    list_filter = ["tipo", "activo", "destacado"]
    search_fields = ["nombre"]


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre_sucursal", "comercio", "ciudad", "activo"]
    list_filter = ["comercio", "ciudad__provincia", "activo"]
    search_fields = ["nombre_sucursal", "ciudad__nombre", "direccion"]
