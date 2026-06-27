from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from django.db.models import Q

from .models import Categoria, Producto
from .serializers import (
    CategoriaSerializer, CategoriaRequestSerializer,
    ProductoSerializer, ProductoRequestSerializer,
)


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
        return Response(
            CategoriaSerializer(categoria).data,
            status=status.HTTP_201_CREATED,
        )


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
        categoria = serializer.save()
        return Response(CategoriaSerializer(categoria).data)

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
        qs = Producto.objects.select_related("categoria").all()
        params = self.request.query_params

        buscar = params.get("buscar")
        if buscar:
            qs = qs.filter(Q(nombre__icontains=buscar) | Q(marca__icontains=buscar))

        categoria = params.get("categoria") or params.get("id_categoria")
        if categoria:
            qs = qs.filter(categoria_id=categoria)

        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(precios__comercio__tipo=tipo).distinct()

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ProductoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response(
            ProductoSerializer(producto).data,
            status=status.HTTP_201_CREATED,
        )


class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related("categoria").all()

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
        producto = serializer.save()
        return Response(ProductoSerializer(producto).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
