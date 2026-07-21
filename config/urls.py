from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "PreciosEC Admin"
admin.site.site_title = "PreciosEC"
admin.site.index_title = "Panel de administración"
# Alimenta {{ site_url }} en admin/base.html -- el link "Ver sitio" del
# header ya es un bloque nativo de Django (userlinks), solo hacía falta
# apuntarlo a la app real en vez del "/" por defecto.
admin.site.site_url = "https://precios-ec.uaeftt-ute.site"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls_auth")),
    path("api/users/", include("apps.users.urls")),
    path("api/categories/", include("apps.categories.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/emails/", include("apps.emails.urls")),
    path("api/kache/", include("apps.catalogo.urls")),
    path("api/kache/", include("apps.comercios.urls")),
    path("api/kache/", include("apps.precios.urls")),
    path("api/kache/", include("apps.comparador.urls")),
    path("api/kache/", include("apps.extras.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
