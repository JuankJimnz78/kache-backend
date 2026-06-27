from django.urls import path
from . import views

urlpatterns = [
    path("", views.ProductListCreateView.as_view()),
    path("available/", views.available_products_view),
    path("stats/", views.product_stats_view),
    path("<int:pk>/", views.ProductDetailView.as_view()),
    path("<int:pk>/restock/", views.restock_view),
]
