from rest_framework import serializers
from .models import Product


class CategorySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ProductSerializer(serializers.ModelSerializer):
    price_with_tax = serializers.FloatField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()
    category = CategorySummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price", "price_with_tax",
            "stock", "in_stock", "is_active", "image", "image_url",
            "category", "created_at", "updated_at",
        ]

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, "url"):
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductRequestSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="category.id", required=False)

    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "is_active", "category_id"]

    def create(self, validated_data):
        cat_data = validated_data.pop("category", None)
        if cat_data:
            validated_data["category_id"] = cat_data["id"]
        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        cat_data = validated_data.pop("category", None)
        if cat_data:
            validated_data["category_id"] = cat_data["id"]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProductStatsSerializer(serializers.Serializer):
    total_active = serializers.IntegerField()
    total_inactive = serializers.IntegerField()
    avg_price = serializers.FloatField(allow_null=True)
    max_price = serializers.FloatField(allow_null=True)
    min_price = serializers.FloatField(allow_null=True)
    total_stock = serializers.IntegerField(allow_null=True)
    out_of_stock = serializers.IntegerField()


class RestockRequestSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
