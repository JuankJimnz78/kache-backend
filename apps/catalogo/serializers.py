from django.db.models import Min
from rest_framework import serializers

from apps.precios.models import precio_efectivo_expression

from .models import Categoria, Producto


# ── Lectura ──────────────────────────────────────────────────────

class CategoriaSerializer(serializers.ModelSerializer):
    id_categoria = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Categoria
        fields = ["id_categoria", "nombre", "descripcion", "categoria_padre"]


class CategoriaDetalleSerializer(serializers.ModelSerializer):
    """Versión liviana, para anidar dentro de ProductoSerializer (categoria_detalle)."""

    id_categoria = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Categoria
        fields = ["id_categoria", "nombre", "descripcion"]


class ProductoSerializer(serializers.ModelSerializer):
    id_producto = serializers.IntegerField(source="id", read_only=True)
    id_categoria = serializers.IntegerField(source="categoria_id", read_only=True)
    categoria_detalle = CategoriaDetalleSerializer(source="categoria", read_only=True)
    precio_desde = serializers.SerializerMethodField()
    tiene_oferta = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id_producto", "nombre", "marca", "codigo_barras", "imagen_url",
            "descripcion", "unidad_medida", "id_categoria", "categoria_detalle",
            "precio_desde", "tiene_oferta",
        ]

    def get_precio_desde(self, obj):
        # ProductoListCreateView ya lo anota (sin N+1). Si el queryset no
        # viene anotado (detalle individual, o anidado en Favorito), se
        # calcula con una sola query aparte — sigue siendo mejor que traer
        # todos los Precio del producto al cliente.
        if hasattr(obj, "precio_desde"):
            return obj.precio_desde
        return obj.precios.aggregate(minimo=Min(precio_efectivo_expression()))["minimo"]

    def get_tiene_oferta(self, obj):
        if hasattr(obj, "tiene_oferta"):
            return obj.tiene_oferta
        return obj.precios.filter(en_oferta=True, precio_oferta__isnull=False).exists()


# ── Escritura (POST / PATCH / PUT) ──────────────────────────────

class CategoriaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "categoria_padre"]


class ProductoRequestSerializer(serializers.ModelSerializer):
    id_categoria = serializers.IntegerField(
        source="categoria_id", required=False, allow_null=True
    )

    class Meta:
        model = Producto
        fields = [
            "nombre", "marca", "codigo_barras", "descripcion",
            "unidad_medida", "id_categoria",
        ]
