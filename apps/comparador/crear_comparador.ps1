# ── 0. Crear carpetas de la nueva app ────────────────────────────
$dirs = @("apps/comparador", "apps/comparador/migrations")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
New-Item -ItemType File -Force -Path "apps/comparador/__init__.py" | Out-Null
New-Item -ItemType File -Force -Path "apps/comparador/migrations/__init__.py" | Out-Null

# ── 1. apps.py ────────────────────────────────────────────────────
@'
from django.apps import AppConfig


class ComparadorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comparador"
    verbose_name = "Kache - Comparador"
'@ | Set-Content -Path "apps/comparador/apps.py" -Encoding UTF8

# ── 2. models.py ──────────────────────────────────────────────────
@'
from django.conf import settings
from django.db import models

from apps.catalogo.models import Producto
from apps.comercios.models import Comercio


class ListaComparacion(models.Model):
    """
    Una lista de comparación que el usuario va armando: para cada producto
    que agrega, elige en qué comercio lo compra. El resultado final se puede
    agrupar por comercio para ver cuánto pagaría en cada uno.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="listas_comparacion",
    )
    nombre = models.CharField(max_length=100, blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre or f"Lista de {self.usuario.username} ({self.fecha_creacion:%d/%m/%Y})"


class ItemComparacion(models.Model):
    """
    Un producto + el comercio elegido por el usuario para comprarlo, dentro
    de una ListaComparacion. precio_momento es una 'foto' del precio al
    momento de agregarlo — si el precio real cambia después, esta lista
    no cambia sola, para que el usuario no se confunda comparando contra
    un número que ya no es el que vio.
    """

    lista = models.ForeignKey(ListaComparacion, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE)
    precio_momento = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["comercio", "producto"]
        unique_together = ["lista", "producto"]

    def __str__(self):
        return f"{self.producto.nombre} -> {self.comercio.nombre} (lista #{self.lista_id})"
'@ | Set-Content -Path "apps/comparador/models.py" -Encoding UTF8

# ── 3. serializers.py ─────────────────────────────────────────────
@'
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
'@ | Set-Content -Path "apps/comparador/serializers.py" -Encoding UTF8

# Nota: el serializer usa Decimal, hace falta el import — lo agregamos aparte:
(Get-Content "apps/comparador/serializers.py") -replace "from rest_framework import serializers", "from decimal import Decimal`nfrom rest_framework import serializers" | Set-Content "apps/comparador/serializers.py" -Encoding UTF8

# ── 4. views.py ───────────────────────────────────────────────────
@'
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ListaComparacion, ItemComparacion
from .serializers import (
    ListaComparacionSerializer, ListaComparacionListSerializer, ListaComparacionRequestSerializer,
    ItemComparacionSerializer, ItemComparacionRequestSerializer,
)
from apps.precios.models import Precio
from apps.catalogo.models import Producto
from apps.comercios.models import Comercio


class ListaComparacionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ListaComparacion.objects.filter(usuario=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ListaComparacionRequestSerializer
        return ListaComparacionListSerializer

    def create(self, request, *args, **kwargs):
        serializer = ListaComparacionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lista = serializer.save(usuario=request.user)
        return Response(ListaComparacionSerializer(lista).data, status=status.HTTP_201_CREATED)


class ListaComparacionDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ListaComparacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ListaComparacion.objects.filter(usuario=self.request.user)


class ItemComparacionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lista_pk):
        try:
            lista = ListaComparacion.objects.get(pk=lista_pk, usuario=request.user)
        except ListaComparacion.DoesNotExist:
            return Response({"detail": "Lista no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        entrada = ItemComparacionRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        id_producto = entrada.validated_data["id_producto"]
        id_comercio = entrada.validated_data["id_comercio"]

        try:
            producto = Producto.objects.get(pk=id_producto)
            comercio = Comercio.objects.get(pk=id_comercio)
        except (Producto.DoesNotExist, Comercio.DoesNotExist):
            return Response({"detail": "Producto o comercio no existe."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            precio = Precio.objects.get(producto=producto, comercio=comercio)
        except Precio.DoesNotExist:
            return Response(
                {"detail": "Este producto no tiene precio registrado en ese comercio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, creado = ItemComparacion.objects.update_or_create(
            lista=lista,
            producto=producto,
            defaults={"comercio": comercio, "precio_momento": precio.precio_efectivo},
        )

        return Response(
            ItemComparacionSerializer(item).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )


class ItemComparacionDeleteView(generics.DestroyAPIView):
    serializer_class = ItemComparacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ItemComparacion.objects.filter(lista__usuario=self.request.user)
'@ | Set-Content -Path "apps/comparador/views.py" -Encoding UTF8

# ── 5. urls.py ────────────────────────────────────────────────────
@'
from django.urls import path
from . import views

urlpatterns = [
    path("listas-comparacion/", views.ListaComparacionListCreateView.as_view()),
    path("listas-comparacion/<int:pk>/", views.ListaComparacionDetailView.as_view()),
    path("listas-comparacion/<int:lista_pk>/items/", views.ItemComparacionCreateView.as_view()),
    path("items-comparacion/<int:pk>/", views.ItemComparacionDeleteView.as_view()),
]
'@ | Set-Content -Path "apps/comparador/urls.py" -Encoding UTF8

# ── 6. admin.py ───────────────────────────────────────────────────
@'
from django.contrib import admin
from .models import ListaComparacion, ItemComparacion


class ItemComparacionInline(admin.TabularInline):
    model = ItemComparacion
    extra = 0
    readonly_fields = ["fecha_agregado"]


@admin.register(ListaComparacion)
class ListaComparacionAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "nombre", "fecha_creacion"]
    list_filter = ["usuario"]
    inlines = [ItemComparacionInline]


@admin.register(ItemComparacion)
class ItemComparacionAdmin(admin.ModelAdmin):
    list_display = ["id", "lista", "producto", "comercio", "precio_momento"]
    list_filter = ["comercio"]
'@ | Set-Content -Path "apps/comparador/admin.py" -Encoding UTF8

Write-Host "Listo: app 'comparador' creada completa." -ForegroundColor Green