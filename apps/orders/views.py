from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count

from .models import Order, OrderItem
from .serializers import (
    OrderSerializer,
    AddItemRequestSerializer,
    UpdateStatusRequestSerializer,
)
from apps.products.models import Product


class OrderPagination(PageNumberPagination):
    page_size = 20


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def order_list_create_view(request):
    """GET: listar ordenes. POST: crear orden vacía (carrito)."""
    if request.method == "POST":
        order = Order.objects.create(user=request.user)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    # GET
    if request.user.is_staff:
        qs = Order.objects.all()
    else:
        qs = Order.objects.filter(user=request.user)

    status_filter = request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = OrderPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = OrderSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail_view(request, pk):
    try:
        if request.user.is_staff:
            order = Order.objects.get(pk=pk)
        else:
            order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_item_view(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user, status="pending")
    except Order.DoesNotExist:
        return Response(
            {"detail": "Orden no encontrada o ya confirmada."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = AddItemRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        product = Product.objects.get(
            pk=serializer.validated_data["product_id"],
            is_active=True,
        )
    except Product.DoesNotExist:
        return Response(
            {"detail": "Producto no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    quantity = serializer.validated_data["quantity"]
    if product.stock < quantity:
        return Response(
            {"detail": f"Stock insuficiente. Disponible: {product.stock}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Si ya existe el item, sumar cantidad
    item, created = OrderItem.objects.get_or_create(
        order=order,
        product=product,
        defaults={"quantity": quantity, "unit_price": product.price},
    )
    if not created:
        item.quantity += quantity
        item.save()

    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_order_view(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user, status="pending")
    except Order.DoesNotExist:
        return Response(
            {"detail": "Orden no encontrada o ya confirmada."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Descontar stock
    for item in order.items.select_related("product").all():
        product = item.product
        if product.stock < item.quantity:
            return Response(
                {"detail": f"Stock insuficiente para {product.name}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.stock -= item.quantity
        product.save()

    order.status = "confirmed"
    order.save()
    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def update_status_view(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateStatusRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    order.status = serializer.validated_data["status"]
    order.save()
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def order_stats_view(request):
    orders = Order.objects.all()
    total_orders = orders.count()

    # Calcular revenue sumando los totales
    total_revenue = 0.0
    for order in orders.filter(status__in=["confirmed", "shipped", "delivered"]):
        total_revenue += order.total

    by_status = {}
    status_counts = orders.values("status").annotate(count=Count("id"))
    for item in status_counts:
        by_status[item["status"]] = item["count"]

    return Response({
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "by_status": by_status,
    })
