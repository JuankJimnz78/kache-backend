from rest_framework import serializers
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

    class Meta:
        model = Producto
        fields = [
            "id_producto", "nombre", "marca", "codigo_barras", "descripcion",
            "unidad_medida", "id_categoria", "categoria_detalle",
        ]


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
