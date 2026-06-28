from django.urls import path
from . import views

urlpatterns = [
    path("", views.UserListCreateView.as_view()),
    path("profile/", views.profile_view),
    path("stats/", views.user_stats_view),
    path("busquedas/", views.busquedas_recientes_view),
    path("busquedas/limpiar/", views.limpiar_busquedas_view),
    path("<int:pk>/", views.UserDetailView.as_view()),
    path("<int:pk>/toggle-active/", views.toggle_active_view),
]
