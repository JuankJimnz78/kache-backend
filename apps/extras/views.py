from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import (
    PerfilUsuario, Publicidad, Favorito, AlertaPrecio,
    Notificacion, ReporteProducto, Resena,
)
from .serializers import (
    PerfilUsuarioSerializer, PublicidadSerializer, FavoritoSerializer,
    AlertaPrecioSerializer, NotificacionSerializer, ReporteProductoSerializer, ResenaSerializer,
)


class PerfilUsuarioView(generics.RetrieveUpdateAPIView):
    serializer_class = PerfilUsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=self.request.user)
        return perfil


class PublicidadListView(generics.ListAPIView):
    """Pública: cualquiera puede ver los banners vigentes (no requiere login)."""
    serializer_class = PublicidadSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Publicidad.objects.filter(activo=True)


class FavoritoListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorito.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class FavoritoDeleteView(generics.DestroyAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorito.objects.filter(usuario=self.request.user)


class AlertaPrecioListCreateView(generics.ListCreateAPIView):
    serializer_class = AlertaPrecioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AlertaPrecio.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class AlertaPrecioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AlertaPrecioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AlertaPrecio.objects.filter(usuario=self.request.user)


class NotificacionPagination(PageNumberPagination):
    """
    Permite al cliente pedir page_size=1 para leer solo el `count` (ej. badge
    de no leídas) sin traer resultados que no necesita. Tope en 100 para que
    nadie pida la tabla completa en una sola página.
    """
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificacionPagination

    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user)
        leida = self.request.query_params.get("leida")
        if leida is not None:
            qs = qs.filter(leida=leida.lower() == "true")
        return qs


class NotificacionMarcarLeidaView(generics.UpdateAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)


class ReporteProductoCreateView(generics.ListCreateAPIView):
    serializer_class = ReporteProductoSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return ReporteProducto.objects.all()

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class ResenaListCreateView(generics.ListCreateAPIView):
    serializer_class = ResenaSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Resena.objects.select_related("usuario").all()
        comercio = self.request.query_params.get("comercio")
        if comercio:
            qs = qs.filter(comercio_id=comercio)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save(usuario=request.user)
        except IntegrityError:
            return Response(
                {"detail": "Ya reseñaste este comercio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )