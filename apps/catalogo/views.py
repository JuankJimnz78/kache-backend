from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from .models import Marca, Etiqueta, Categoria, Producto
from apps.precios.models import Precio
from .serializers import (
    MarcaSerializer, MarcaRequestSerializer,
    EtiquetaSerializer, EtiquetaRequestSerializer,
    CategoriaSerializer, CategoriaRequestSerializer,
    ProductoSerializer, ProductoRequestSerializer,
)


class MarcaListCreateView(generics.ListCreateAPIView):
    queryset = Marca.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MarcaRequestSerializer
        return MarcaSerializer

    def create(self, request, *args, **kwargs):
        serializer = MarcaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        marca = serializer.save()
        return Response(MarcaSerializer(marca).data, status=status.HTTP_201_CREATED)


class MarcaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Marca.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return MarcaRequestSerializer
        return MarcaSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = MarcaRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(MarcaSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class EtiquetaListCreateView(generics.ListCreateAPIView):
    queryset = Etiqueta.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EtiquetaRequestSerializer
        return EtiquetaSerializer

    def create(self, request, *args, **kwargs):
        serializer = EtiquetaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        etiqueta = serializer.save()
        return Response(EtiquetaSerializer(etiqueta).data, status=status.HTTP_201_CREATED)


class EtiquetaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Etiqueta.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return EtiquetaRequestSerializer
        return EtiquetaSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = EtiquetaRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(EtiquetaSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class CategoriaListCreateView(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CategoriaRequestSerializer
        return CategoriaSerializer

    def create(self, request, *args, **kwargs):
        serializer = CategoriaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        categoria = serializer.save()
        return Response(CategoriaSerializer(categoria).data, status=status.HTTP_201_CREATED)


class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CategoriaRequestSerializer
        return CategoriaSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = CategoriaRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(CategoriaSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class ProductoListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductoRequestSerializer
        return ProductoSerializer

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria", "marca").prefetch_related("etiquetas").all()
        params = self.request.query_params

        buscar = params.get("buscar")
        if buscar:
            qs = qs.filter(
                Q(nombre__icontains=buscar) | Q(marca__nombre__icontains=buscar)
            )

        categoria = params.get("categoria") or params.get("id_categoria")
        if categoria:
            qs = qs.filter(categoria_id=categoria)

        marca = params.get("marca") or params.get("id_marca")
        if marca:
            qs = qs.filter(marca_id=marca)

        etiqueta = params.get("etiqueta")
        if etiqueta:
            qs = qs.filter(etiquetas__nombre__icontains=etiqueta).distinct()

        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(precios__comercio__tipo=tipo).distinct()

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ProductoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response(ProductoSerializer(producto).data, status=status.HTTP_201_CREATED)


class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related("categoria", "marca").prefetch_related("etiquetas").all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProductoRequestSerializer
        return ProductoSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = ProductoRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(ProductoSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class ComparacionProductoView(APIView):
    """
    GET /api/kache/productos/<pk>/comparar/

    Devuelve el producto y sus precios en todos los comercios donde está
    registrado, ordenados de menor a mayor precio efectivo.
    Marca el más barato con `es_mas_barato: true`.

    Cálculo al vuelo — no persiste nada. Requiere que los productos
    hayan sido unificados previamente (uv run manage.py unificar_productos_demo).
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            producto = (
                Producto.objects
                .select_related("categoria", "marca")
                .prefetch_related("etiquetas")
                .get(pk=pk)
            )
        except Producto.DoesNotExist:
            return Response(
                {"detail": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        precios_qs = (
            Precio.objects
            .filter(producto=producto)
            .select_related("comercio")
        )

        # precio_efectivo es una @property — se evalúa en Python, no en SQL
        entradas = []
        for p in precios_qs:
            entradas.append({
                "id_comercio":     p.comercio_id,
                "nombre_comercio": p.comercio.nombre,
                "logo_url":        p.comercio.logo_url,
                "precio_efectivo": p.precio_efectivo,
                "precio_normal":   p.precio_actual,
                "en_oferta":       p.en_oferta,
            })

        entradas.sort(key=lambda x: x["precio_efectivo"])

        mejor_precio = entradas[0]["precio_efectivo"] if entradas else None
        for entrada in entradas:
            entrada["es_mas_barato"] = (entrada["precio_efectivo"] == mejor_precio)

        return Response({
            "id_producto":          producto.id,
            "nombre":               producto.nombre,
            "unidad_medida":        producto.unidad_medida,
            "codigo_barras":        producto.codigo_barras,
            "mejor_precio":         mejor_precio,
            "total_comercios":      len(entradas),
            "precios_por_comercio": entradas,
        })
