from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view),
    path("register/", views.register_view),
    path("logout/", views.logout_view),
    path("token/refresh/", views.token_refresh_view),
    path("password-reset/", views.password_reset_request_view),
    path("password-reset/confirm/", views.password_reset_confirm_view),
]
