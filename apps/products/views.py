from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Sum, Q

from .models import Product
from .serializers import (
    ProductSerializer,
    ProductRequestSerializer,
    RestockRequestSerializer,
)


class ProductListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductRequestSerializer
        return ProductSerializer

    def get_queryset(self):
        qs = Product.objects.select_related("category").all()
        params = self.request.query_params

        search = params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        category = params.get("category")
        if category:
            qs = qs.filter(category_id=category)

        price_min = params.get("price_min")
        if price_min:
            qs = qs.filter(price__gte=price_min)

        price_max = params.get("price_max")
        if price_max:
            qs = qs.filter(price__lte=price_max)

        stock_min = params.get("stock_min")
        if stock_min:
            qs = qs.filter(stock__gte=stock_min)

        is_active = params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        ordering = params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        page_size = params.get("page_size")
        if page_size:
            self.pagination_class.page_size = int(page_size)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ProductRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            ProductSerializer(product, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("category").all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProductRequestSerializer
        return ProductSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = ProductRequestSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product, context={"request": request}).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([AllowAny])
def available_products_view(request):
    """Productos activos con stock > 0."""
    qs = Product.objects.select_related("category").filter(is_active=True, stock__gt=0)
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = ProductSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def restock_view(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = RestockRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    product.stock += serializer.validated_data["quantity"]
    product.save()
    return Response({
        "id": product.id,
        "name": product.name,
        "new_stock": product.stock,
    })


@api_view(["GET"])
@permission_classes([IsAdminUser])
def product_stats_view(request):
    products = Product.objects.all()
    agg = products.aggregate(
        avg_price=Avg("price"),
        max_price=Max("price"),
        min_price=Min("price"),
        total_stock=Sum("stock"),
    )
    return Response({
        "total_active": products.filter(is_active=True).count(),
        "total_inactive": products.filter(is_active=False).count(),
        "avg_price": float(agg["avg_price"]) if agg["avg_price"] else None,
        "max_price": float(agg["max_price"]) if agg["max_price"] else None,
        "min_price": float(agg["min_price"]) if agg["min_price"] else None,
        "total_stock": agg["total_stock"] or 0,
        "out_of_stock": products.filter(stock=0).count(),
    })
