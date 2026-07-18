from rest_framework import serializers
from .models import Comercio, Sucursal


# ── Lectura ──────────────────────────────────────────────────────

class ComercioSerializer(serializers.ModelSerializer):
    id_comercio = serializers.IntegerField(source="id", read_only=True)
    destacado_activo = serializers.BooleanField(read_only=True)
    promedio_calificacion = serializers.SerializerMethodField()
    total_resenas = serializers.SerializerMethodField()

    class Meta:
        model = Comercio
        fields = [
            "id_comercio", "nombre", "tipo", "logo_url", "sitio_web", "activo",
            "destacado", "fecha_fin_destacado", "destacado_activo",
            "promedio_calificacion", "total_resenas",
        ]

    def get_promedio_calificacion(self, obj):
        # ComercioListCreateView ya lo anota (sin N+1). Si el queryset no
        # viene anotado (detalle individual), se calcula con una sola query
        # aparte — sigue siendo mejor que traer todas las reseñas al cliente.
        if hasattr(obj, "promedio_calificacion"):
            return obj.promedio_calificacion
        from django.db.models import Avg
        return obj.resenas.aggregate(promedio=Avg("calificacion"))["promedio"]

    def get_total_resenas(self, obj):
        if hasattr(obj, "total_resenas"):
            return obj.total_resenas
        return obj.resenas.count()


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