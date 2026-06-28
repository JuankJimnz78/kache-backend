from rest_framework import serializers
from .models import Marca, Etiqueta, Categoria, Producto


# ── Lectura ──────────────────────────────────────────────────────

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ["id", "nombre", "pais_origen", "sitio_web"]


class EtiquetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etiqueta
        fields = ["id", "nombre", "descripcion"]


class CategoriaSerializer(serializers.ModelSerializer):
    id_categoria = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Categoria
        fields = ["id_categoria", "nombre", "descripcion", "categoria_padre"]


class CategoriaDetalleSerializer(serializers.ModelSerializer):
    id_categoria = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Categoria
        fields = ["id_categoria", "nombre", "descripcion"]


class ProductoSerializer(serializers.ModelSerializer):
    id_producto = serializers.IntegerField(source="id", read_only=True)
    id_categoria = serializers.IntegerField(source="categoria_id", read_only=True)
    id_marca = serializers.IntegerField(source="marca_id", read_only=True)
    categoria_detalle = CategoriaDetalleSerializer(source="categoria", read_only=True)
    marca_detalle = MarcaSerializer(source="marca", read_only=True)
    etiquetas = EtiquetaSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id_producto", "nombre", "id_marca", "marca_detalle",
            "codigo_barras", "descripcion", "unidad_medida",
            "id_categoria", "categoria_detalle", "etiquetas",
        ]


# ── Escritura (POST / PATCH / PUT) ──────────────────────────────

class MarcaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ["nombre", "pais_origen", "sitio_web"]


class EtiquetaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etiqueta
        fields = ["nombre", "descripcion"]


class CategoriaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "categoria_padre"]


class ProductoRequestSerializer(serializers.ModelSerializer):
    id_categoria = serializers.IntegerField(
        source="categoria_id", required=False, allow_null=True
    )
    id_marca = serializers.IntegerField(
        source="marca_id", required=False, allow_null=True
    )
    etiquetas = serializers.PrimaryKeyRelatedField(
        queryset=Etiqueta.objects.all(), many=True, required=False
    )

    class Meta:
        model = Producto
        fields = [
            "nombre", "id_marca", "codigo_barras", "descripcion",
            "unidad_medida", "id_categoria", "etiquetas",
        ]

    def create(self, validated_data):
        etiquetas = validated_data.pop("etiquetas", [])
        producto = Producto.objects.create(**validated_data)
        producto.etiquetas.set(etiquetas)
        return producto

    def update(self, instance, validated_data):
        etiquetas = validated_data.pop("etiquetas", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if etiquetas is not None:
            instance.etiquetas.set(etiquetas)
        return instance
