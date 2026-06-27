from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "is_active", "category")
    list_filter = ("is_active", "category")
    search_fields = ("name",)
