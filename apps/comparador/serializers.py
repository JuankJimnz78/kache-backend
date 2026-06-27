from decimal import Decimal

from rest_framework import serializers

from .models import ListaComparacion, ItemComparacion
from apps.catalogo.serializers import ProductoSerializer
from apps.comercios.serializers import ComercioDetalleSerializer


class ItemComparacionSerializer(serializers.ModelSerializer):
    id_item = serializers.IntegerField(source="id", read_only=True)
    producto_detalle = ProductoSerializer(source="producto", read_only=True)
    comercio_detalle = ComercioDetalleSerializer(source="comercio", read_only=True)

    class Meta:
        model = ItemComparacion
        fields = ["id_item", "producto_detalle", "comercio_detalle", "precio_momento", "fecha_agregado"]


class ItemComparacionRequestSerializer(serializers.Serializer):
    """Solo recibe id_producto e id_comercio — el precio lo calcula el
    backend a partir del Precio real, nunca se confía en lo que mande el cliente."""
    id_producto = serializers.IntegerField()
    id_comercio = serializers.IntegerField()


class ListaComparacionSerializer(serializers.ModelSerializer):
    """Detalle completo: incluye items y los totales agrupados por comercio."""
    id_lista = serializers.IntegerField(source="id", read_only=True)
    items = ItemComparacionSerializer(many=True, read_only=True)
    totales_por_comercio = serializers.SerializerMethodField()

    class Meta:
        model = ListaComparacion
        fields = ["id_lista", "nombre", "fecha_creacion", "items", "totales_por_comercio"]

    def get_totales_por_comercio(self, obj):
        totales = {}
        for item in obj.items.all():
            key = item.comercio_id
            if key not in totales:
                totales[key] = {
                    "id_comercio": item.comercio_id,
                    "nombre_comercio": item.comercio.nombre,
                    "cantidad_productos": 0,
                    "total": Decimal("0"),
                }
            totales[key]["cantidad_productos"] += 1
            totales[key]["total"] += item.precio_momento
        return list(totales.values())


class ListaComparacionListSerializer(serializers.ModelSerializer):
    """Versión liviana para el listado — sin items completos, solo conteo."""
    id_lista = serializers.IntegerField(source="id", read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = ListaComparacion
        fields = ["id_lista", "nombre", "fecha_creacion", "total_items"]

    def get_total_items(self, obj):
        return obj.items.count()


class ListaComparacionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaComparacion
        fields = ["nombre"]