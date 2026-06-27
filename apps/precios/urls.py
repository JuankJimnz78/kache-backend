from django.urls import path
from . import views

urlpatterns = [
    path("precios/", views.PrecioListCreateView.as_view()),
    path("precios/<int:pk>/", views.PrecioDetailView.as_view()),
    path("historial-precios/", views.HistorialPrecioListView.as_view()),
]