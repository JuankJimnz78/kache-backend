from django.db import models
from django.utils import timezone


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)

    class Meta:
        ordering = ["provincia", "nombre"]
        unique_together = ["nombre", "provincia"]
        verbose_name_plural = "ciudades"

    def __str__(self):
        return f"{self.nombre} ({self.provincia})"


class Comercio(models.Model):
    """Cadena/negocio comparado en Kache (ej. Supermaxi, Fybeca, Kywi)."""

    TIPO_SUPERMERCADO = "supermercado"
    TIPO_FARMACIA = "farmacia"
    TIPO_FERRETERIA = "ferreteria"
    TIPO_CHOICES = [
        (TIPO_SUPERMERCADO, "Supermercado"),
        (TIPO_FARMACIA, "Farmacia"),
        (TIPO_FERRETERIA, "Ferretería"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    logo_url = models.URLField(blank=True, null=True)
    sitio_web = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    destacado = models.BooleanField(default=False)
    fecha_fin_destacado = models.DateField(
        null=True, blank=True,
        help_text="Si se deja vacío, el destacado no vence solo.",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    @property
    def destacado_activo(self):
        if not self.destacado:
            return False
        if self.fecha_fin_destacado is None:
            return True
        return self.fecha_fin_destacado >= timezone.now().date()


class Sucursal(models.Model):
    """Ubicación física de un Comercio."""

    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="sucursales")
    nombre_sucursal = models.CharField(max_length=100)
    ciudad = models.ForeignKey(
        Ciudad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sucursales",
    )
    direccion = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ciudad", "nombre_sucursal"]
        verbose_name_plural = "sucursales"

    def __str__(self):
        ciudad_str = self.ciudad.nombre if self.ciudad else "—"
        return f"{self.nombre_sucursal} - {ciudad_str}"
