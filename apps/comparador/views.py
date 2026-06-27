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