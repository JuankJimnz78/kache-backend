from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import Precio, HistorialPrecio
from .serializers import (
    PrecioSerializer, PrecioRequestSerializer, HistorialPrecioSerializer,
)


class PrecioListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PrecioRequestSerializer
        return PrecioSerializer

    def get_queryset(self):
        qs = Precio.objects.select_related("producto", "comercio").all()
        params = self.request.query_params

        producto = params.get("producto") or params.get("id_producto")
        if producto:
            qs = qs.filter(producto_id=producto)

        comercio = params.get("comercio") or params.get("id_comercio")
        if comercio:
            qs = qs.filter(comercio_id=comercio)

        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(comercio__tipo=tipo)

        en_oferta = params.get("en_oferta")
        if en_oferta is not None:
            qs = qs.filter(en_oferta=en_oferta.lower() == "true")

        return qs.order_by("precio_actual")

    def create(self, request, *args, **kwargs):
        serializer = PrecioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        precio = serializer.save()
        return Response(
            PrecioSerializer(precio).data,
            status=status.HTTP_201_CREATED,
        )


class PrecioDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Precio.objects.select_related("producto", "comercio").all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return PrecioRequestSerializer
        return PrecioSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = PrecioRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        precio = serializer.save()
        return Response(PrecioSerializer(precio).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class HistorialPrecioListView(generics.ListAPIView):
    """Solo lectura: el historial se genera solo, vía señal en models.py."""

    serializer_class = HistorialPrecioSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = HistorialPrecio.objects.select_related("producto", "comercio").all()
        params = self.request.query_params

        producto = params.get("producto") or params.get("id_producto")
        if producto:
            qs = qs.filter(producto_id=producto)

        comercio = params.get("comercio") or params.get("id_comercio")
        if comercio:
            qs = qs.filter(comercio_id=comercio)

        return qs