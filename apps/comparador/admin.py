from django.contrib import admin
from .models import ListaComparacion, ItemComparacion


class ItemComparacionInline(admin.TabularInline):
    model = ItemComparacion
    extra = 0
    readonly_fields = ["fecha_agregado"]


@admin.register(ListaComparacion)
class ListaComparacionAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "nombre", "fecha_creacion"]
    list_filter = ["usuario"]
    inlines = [ItemComparacionInline]


@admin.register(ItemComparacion)
class ItemComparacionAdmin(admin.ModelAdmin):
    list_display = ["id", "lista", "producto", "comercio", "precio_momento"]
    list_filter = ["comercio"]