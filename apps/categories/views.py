from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response

from .models import Category
from .serializers import CategorySerializer, CategoryRequestSerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CategoryRequestSerializer
        return CategorySerializer

    def create(self, request, *args, **kwargs):
        serializer = CategoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cat = serializer.save()
        return Response(
            CategorySerializer(cat).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CategoryRequestSerializer
        return CategorySerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = CategoryRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        cat = serializer.save()
        return Response(CategorySerializer(cat).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def category_stats_view(request):
    cats = Category.objects.all()
    total = cats.count()
    active = cats.filter(is_active=True).count()
    inactive = cats.filter(is_active=False).count()
    detail = [
        {
            "id": c.id,
            "name": c.name,
            "num_products": c.products.count(),
            "is_active": c.is_active,
        }
        for c in cats
    ]
    return Response({
        "total": total,
        "active": active,
        "inactive": inactive,
        "detail": detail,
    })
