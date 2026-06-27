from django.urls import path
from . import views

urlpatterns = [
    path("comercios/", views.ComercioListCreateView.as_view()),
    path("comercios/<int:pk>/", views.ComercioDetailView.as_view()),
    path("sucursales/", views.SucursalListCreateView.as_view()),
    path("sucursales/<int:pk>/", views.SucursalDetailView.as_view()),
]
