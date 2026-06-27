from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    total_products = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "is_active", "total_products", "created_at"]

    def get_total_products(self, obj):
        return obj.products.count() if hasattr(obj, "products") else 0


class CategoryRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "is_active"]


class CategoryStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    detail = serializers.ListField()
