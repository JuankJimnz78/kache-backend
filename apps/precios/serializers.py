from rest_framework import serializers
from .models import Precio, HistorialPrecio
from apps.catalogo.serializers import ProductoSerializer
from apps.comercios.serializers import ComercioDetalleSerializer


class PrecioSerializer(serializers.ModelSerializer):
    id_precio = serializers.IntegerField(source="id", read_only=True)
    id_producto = serializers.IntegerField(source="producto_id", read_only=True)
    id_comercio = serializers.IntegerField(source="comercio_id", read_only=True)
    precio_efectivo = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    producto_detalle = ProductoSerializer(source="producto", read_only=True)
    comercio_detalle = ComercioDetalleSerializer(source="comercio", read_only=True)

    class Meta:
        model = Precio
        fields = [
            "id_precio", "id_producto", "id_comercio", "precio_actual",
            "precio_oferta", "en_oferta", "precio_efectivo",
            "fecha_actualizacion", "producto_detalle", "comercio_detalle",
        ]


class HistorialPrecioSerializer(serializers.ModelSerializer):
    id_historial = serializers.IntegerField(source="id", read_only=True)
    id_producto = serializers.IntegerField(source="producto_id", read_only=True)
    id_comercio = serializers.IntegerField(source="comercio_id", read_only=True)

    class Meta:
        model = HistorialPrecio
        fields = ["id_historial", "id_producto", "id_comercio", "precio_registrado", "fecha_registro"]


class PrecioRequestSerializer(serializers.ModelSerializer):
    id_producto = serializers.IntegerField(source="producto_id")
    id_comercio = serializers.IntegerField(source="comercio_id")

    class Meta:
        model = Precio
        fields = ["id_producto", "id_comercio", "precio_actual", "precio_oferta", "en_oferta"] 