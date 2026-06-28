from django.urls import path
from . import views

urlpatterns = [
    path("marcas/", views.MarcaListCreateView.as_view()),
    path("marcas/<int:pk>/", views.MarcaDetailView.as_view()),
    path("etiquetas/", views.EtiquetaListCreateView.as_view()),
    path("etiquetas/<int:pk>/", views.EtiquetaDetailView.as_view()),
    path("categorias/", views.CategoriaListCreateView.as_view()),
    path("categorias/<int:pk>/", views.CategoriaDetailView.as_view()),
    path("productos/", views.ProductoListCreateView.as_view()),
    path("productos/<int:pk>/comparar/", views.ComparacionProductoView.as_view()),
    path("productos/<int:pk>/", views.ProductoDetailView.as_view()),
]
