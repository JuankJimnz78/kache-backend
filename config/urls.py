from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls_auth")),
    path("api/users/", include("apps.users.urls")),
    path("api/emails/", include("apps.emails.urls")),
    path("api/kache/", include("apps.catalogo.urls")),
    path("api/kache/", include("apps.comercios.urls")),
    path("api/kache/", include("apps.precios.urls")),
    path("api/kache/", include("apps.comparador.urls")),
    path("api/kache/", include("apps.extras.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
