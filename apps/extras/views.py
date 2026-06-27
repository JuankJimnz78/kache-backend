from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

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


class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)


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
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Resena.objects.all()
        comercio = self.request.query_params.get("comercio")
        if comercio:
            qs = qs.filter(comercio_id=comercio)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)