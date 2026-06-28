from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import Ciudad, Comercio, Sucursal
from .serializers import (
    CiudadSerializer, CiudadRequestSerializer,
    ComercioSerializer, ComercioRequestSerializer,
    SucursalSerializer, SucursalRequestSerializer,
)


class CiudadListCreateView(generics.ListCreateAPIView):
    queryset = Ciudad.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CiudadRequestSerializer
        return CiudadSerializer

    def create(self, request, *args, **kwargs):
        serializer = CiudadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ciudad = serializer.save()
        return Response(CiudadSerializer(ciudad).data, status=status.HTTP_201_CREATED)


class CiudadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ciudad.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CiudadRequestSerializer
        return CiudadSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = CiudadRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(CiudadSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class ComercioListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ComercioRequestSerializer
        return ComercioSerializer

    def get_queryset(self):
        from django.db.models import Case, When, IntegerField, Q
        from django.utils import timezone

        qs = Comercio.objects.all()
        params = self.request.query_params

        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        activo = params.get("activo")
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == "true")

        hoy = timezone.now().date()
        qs = qs.annotate(
            _orden_destacado=Case(
                When(
                    Q(destacado=True) & (Q(fecha_fin_destacado__isnull=True) | Q(fecha_fin_destacado__gte=hoy)),
                    then=0,
                ),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_orden_destacado", "nombre")

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ComercioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comercio = serializer.save()
        return Response(ComercioSerializer(comercio).data, status=status.HTTP_201_CREATED)


class ComercioDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comercio.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ComercioRequestSerializer
        return ComercioSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = ComercioRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(ComercioSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class SucursalListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SucursalRequestSerializer
        return SucursalSerializer

    def get_queryset(self):
        qs = Sucursal.objects.select_related("comercio", "ciudad").all()
        params = self.request.query_params

        comercio = params.get("comercio") or params.get("id_comercio")
        if comercio:
            qs = qs.filter(comercio_id=comercio)

        ciudad = params.get("ciudad") or params.get("id_ciudad")
        if ciudad:
            if ciudad.isdigit():
                qs = qs.filter(ciudad_id=ciudad)
            else:
                qs = qs.filter(ciudad__nombre__icontains=ciudad)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = SucursalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sucursal = serializer.save()
        return Response(SucursalSerializer(sucursal).data, status=status.HTTP_201_CREATED)


class SucursalDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sucursal.objects.select_related("comercio", "ciudad").all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return SucursalRequestSerializer
        return SucursalSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = SucursalRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(SucursalSerializer(serializer.save()).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
