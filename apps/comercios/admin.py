from django.contrib import admin
from django.utils.html import format_html
from .models import Comercio, Sucursal


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "tipo", "activo", "destacado", "logo_preview"]
    fields = [
        "nombre", "tipo", "logo", "logo_preview", "logo_url",
        "sitio_web", "activo", "destacado", "fecha_fin_destacado",
    ]
    readonly_fields = ["logo_preview", "logo_url"]
    list_filter = ["tipo", "activo", "destacado"]
    search_fields = ["nombre"]

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;object-fit:contain;" />',
                obj.logo.url,
            )
        return "—"


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre_sucursal", "comercio", "ciudad", "activo"]
    list_filter = ["comercio", "ciudad", "activo"]
    search_fields = ["nombre_sucursal", "ciudad", "direccion"]