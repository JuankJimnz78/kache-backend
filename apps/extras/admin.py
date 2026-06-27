from django.contrib import admin
from .models import (
    PerfilUsuario, Publicidad, Favorito, AlertaPrecio,
    Notificacion, ReporteProducto, Resena,
)

admin.site.register(PerfilUsuario)
admin.site.register(Publicidad)
admin.site.register(Favorito)
admin.site.register(AlertaPrecio)
admin.site.register(Notificacion)
admin.site.register(ReporteProducto)
admin.site.register(Resena)