from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.comercios.models import Comercio


class PerfilUsuario(models.Model):
    """Datos adicionales del usuario que no viven en el modelo de auth."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    telefono = models.CharField(max_length=20, blank=True, default="")
    ciudad = models.CharField(max_length=100, blank=True, default="")
    foto_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Publicidad(models.Model):
    """Banner publicitario: de un comercio de Kache destacándose, o de un tercero."""

    titulo = models.CharField(max_length=150)
    imagen_url = models.URLField()
    url_destino = models.URLField(blank=True, null=True)
    comercio = models.ForeignKey(
        Comercio, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Vacío si es publicidad de un tercero, no de un comercio de Kache.",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "publicidad"

    def __str__(self):
        return self.titulo

    @property
    def vigente(self):
        hoy = timezone.now().date()
        return self.activo and self.fecha_inicio <= hoy <= self.fecha_fin


class Favorito(models.Model):
    """Un usuario sigue un producto para no perderlo de vista."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoritos")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["usuario", "producto"]

    def __str__(self):
        return f"{self.usuario.username} -> {self.producto.nombre}"


class AlertaPrecio(models.Model):
    """El usuario define un precio objetivo; se le notifica cuando se alcanza."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alertas_precio")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    comercio = models.ForeignKey(
        Comercio, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Vacío = alerta sobre el precio más barato entre todos los comercios.",
    )
    precio_objetivo = models.DecimalField(max_digits=10, decimal_places=2)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.producto.nombre} <= {self.precio_objetivo} ({self.usuario.username})"


class Notificacion(models.Model):
    """Mensaje interno mostrado al usuario dentro de la app."""

    TIPO_ALERTA_PRECIO = "alerta_precio"
    TIPO_OFERTA = "oferta"
    TIPO_SISTEMA = "sistema"
    TIPO_CHOICES = [
        (TIPO_ALERTA_PRECIO, "Alerta de precio"),
        (TIPO_OFERTA, "Oferta"),
        (TIPO_SISTEMA, "Sistema"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_SISTEMA)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.titulo} -> {self.usuario.username}"


class ReporteProducto(models.Model):
    """Un usuario reporta que un precio está mal o el producto no está disponible."""

    MOTIVO_PRECIO_INCORRECTO = "precio_incorrecto"
    MOTIVO_NO_DISPONIBLE = "no_disponible"
    MOTIVO_OTRO = "otro"
    MOTIVO_CHOICES = [
        (MOTIVO_PRECIO_INCORRECTO, "Precio incorrecto"),
        (MOTIVO_NO_DISPONIBLE, "Producto no disponible"),
        (MOTIVO_OTRO, "Otro"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE)
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    comentario = models.TextField(blank=True, default="")
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    resuelto = models.BooleanField(default=False)

    def __str__(self):
        return f"Reporte: {self.producto.nombre} @ {self.comercio.nombre}"


class Resena(models.Model):
    """Calificación de un usuario sobre un comercio."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="resenas")
    calificacion = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True, default="")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["usuario", "comercio"]
        verbose_name_plural = "reseñas"

    def __str__(self):
        return f"{self.comercio.nombre}: {self.calificacion}/5 ({self.usuario.username})"