from rest_framework import serializers
from .models import Order, OrderItem


class ProductInItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.IntegerField()
    is_active = serializers.BooleanField()


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductInItemSerializer(read_only=True)
    subtotal = serializers.FloatField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "unit_price", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    total = serializers.SerializerMethodField()
    num_items = serializers.IntegerField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "username", "status", "total", "num_items",
            "items", "created_at", "updated_at",
        ]

    def get_total(self, obj):
        return str(obj.total)


class AddItemRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class UpdateStatusRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)


class OrderStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    by_status = serializers.DictField()
