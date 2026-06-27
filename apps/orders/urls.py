from django.urls import path
from . import views

urlpatterns = [
    path("", views.order_list_create_view),
    path("stats/", views.order_stats_view),
    path("<int:pk>/", views.order_detail_view),
    path("<int:pk>/add-item/", views.add_item_view),
    path("<int:pk>/confirm/", views.confirm_order_view),
    path("<int:pk>/update-status/", views.update_status_view),
]
