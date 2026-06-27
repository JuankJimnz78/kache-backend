from django.urls import path
from . import views

urlpatterns = [
    path("categorias/", views.CategoriaListCreateView.as_view()),
    path("categorias/<int:pk>/", views.CategoriaDetailView.as_view()),
    path("productos/", views.ProductoListCreateView.as_view()),
    path("productos/<int:pk>/", views.ProductoDetailView.as_view()),
]
