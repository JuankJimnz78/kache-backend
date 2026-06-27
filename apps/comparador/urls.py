from django.urls import path
from . import views

urlpatterns = [
    path("listas-comparacion/", views.ListaComparacionListCreateView.as_view()),
    path("listas-comparacion/<int:pk>/", views.ListaComparacionDetailView.as_view()),
    path("listas-comparacion/<int:lista_pk>/items/", views.ItemComparacionCreateView.as_view()),
    path("items-comparacion/<int:pk>/", views.ItemComparacionDeleteView.as_view()),
]