from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, BusquedaReciente


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(BusquedaReciente)
class BusquedaRecienteAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "termino", "num_resultados", "fecha"]
    list_filter = ["fecha"]
    search_fields = ["termino", "usuario__username"]
    readonly_fields = ["fecha"]
