from rest_framework import serializers
from .models import Comercio, Sucursal


# ── Lectura ──────────────────────────────────────────────────────

class ComercioSerializer(serializers.ModelSerializer):
    id_comercio = serializers.IntegerField(source="id", read_only=True)
    destacado_activo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Comercio
        fields = [
            "id_comercio", "nombre", "tipo", "logo_url", "sitio_web", "activo",
            "destacado", "fecha_fin_destacado", "destacado_activo",
        ]


class ComercioDetalleSerializer(serializers.ModelSerializer):
    """Versión liviana, para anidar dentro de SucursalSerializer (comercio_detalle)."""

    id_comercio = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Comercio
        fields = ["id_comercio", "nombre", "tipo", "logo_url"]


class SucursalSerializer(serializers.ModelSerializer):
    id_sucursal = serializers.IntegerField(source="id", read_only=True)
    id_comercio = serializers.IntegerField(source="comercio_id", read_only=True)
    comercio_detalle = ComercioDetalleSerializer(source="comercio", read_only=True)

    class Meta:
        model = Sucursal
        fields = [
            "id_sucursal", "id_comercio", "nombre_sucursal", "ciudad",
            "direccion", "activo", "comercio_detalle",
        ]


# ── Escritura (POST / PATCH / PUT) ──────────────────────────────

class ComercioRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comercio
        fields = [
            "nombre", "tipo", "logo_url", "sitio_web", "activo",
            "destacado", "fecha_fin_destacado",
        ]


class SucursalRequestSerializer(serializers.ModelSerializer):
    id_comercio = serializers.IntegerField(source="comercio_id")

    class Meta:
        model = Sucursal
        fields = ["id_comercio", "nombre_sucursal", "ciudad", "direccion", "activo"]