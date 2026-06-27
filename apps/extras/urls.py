from django.urls import path
from . import views

urlpatterns = [
    path("perfil/", views.PerfilUsuarioView.as_view()),
    path("publicidad/", views.PublicidadListView.as_view()),
    path("favoritos/", views.FavoritoListCreateView.as_view()),
    path("favoritos/<int:pk>/", views.FavoritoDeleteView.as_view()),
    path("alertas-precio/", views.AlertaPrecioListCreateView.as_view()),
    path("alertas-precio/<int:pk>/", views.AlertaPrecioDetailView.as_view()),
    path("notificaciones/", views.NotificacionListView.as_view()),
    path("notificaciones/<int:pk>/", views.NotificacionMarcarLeidaView.as_view()),
    path("reportes/", views.ReporteProductoCreateView.as_view()),
    path("resenas/", views.ResenaListCreateView.as_view()),
]