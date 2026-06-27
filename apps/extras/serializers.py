from rest_framework import serializers

from .models import (
    PerfilUsuario, Publicidad, Favorito, AlertaPrecio,
    Notificacion, ReporteProducto, Resena,
)


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilUsuario
        fields = ["id", "telefono", "ciudad", "foto_url"]


class PublicidadSerializer(serializers.ModelSerializer):
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Publicidad
        fields = ["id", "titulo", "imagen_url", "url_destino", "comercio",
                  "fecha_inicio", "fecha_fin", "activo", "vigente"]


class FavoritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorito
        fields = ["id", "producto", "fecha_agregado"]


class AlertaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaPrecio
        fields = ["id", "producto", "comercio", "precio_objetivo", "activa", "fecha_creacion"]


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ["id", "titulo", "mensaje", "tipo", "leida", "fecha_creacion"]


class ReporteProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporteProducto
        fields = ["id", "producto", "comercio", "motivo", "comentario", "fecha_reporte", "resuelto"]


class ResenaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resena
        fields = ["id", "comercio", "calificacion", "comentario", "fecha"]