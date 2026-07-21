from django.db import models
from django.utils import timezone


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
    logo_url = models.URLField(
        blank=True, null=True,
        help_text="Se recalcula solo a partir de 'logo' al guardar -- no editar a mano.",
    )
    logo = models.ImageField(
        upload_to="comercios/logos/", blank=True, null=True,
        help_text="Subir un archivo acá lo sube a R2 y actualiza logo_url automáticamente.",
    )
    sitio_web = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    # Publicidad: el comercio paga por aparecer destacado en el selector
    # de categorías. fecha_fin_destacado permite que la promoción se
    # desactive sola sin que nadie tenga que acordarse de desmarcarla.
    destacado = models.BooleanField(default=False)
    fecha_fin_destacado = models.DateField(
        null=True, blank=True,
        help_text="Si se deja vacío, el destacado no vence solo.",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def save(self, *args, **kwargs):
        # El upload_to (y por lo tanto el nombre final del archivo en R2)
        # recién se resuelve DENTRO de super().save() -- self.logo.url no es
        # confiable antes de eso. Por eso se guarda primero y, si logo_url
        # quedó desactualizado, se corrige con un .update() (no otro save(),
        # para no reentrar en este método).
        super().save(*args, **kwargs)
        if self.logo and self.logo_url != self.logo.url:
            self.logo_url = self.logo.url
            type(self).objects.filter(pk=self.pk).update(logo_url=self.logo_url)

    @property
    def destacado_activo(self):
        """True solo si destacado=True Y (no tiene fecha de fin, o esa fecha no ha pasado)."""
        if not self.destacado:
            return False
        if self.fecha_fin_destacado is None:
            return True
        return self.fecha_fin_destacado >= timezone.now().date()


class Sucursal(models.Model):
    """
    Ubicación física de un Comercio. Ya NO determina el precio (eso lo hace
    Comercio directamente vía apps.precios.Precio) — sucursal es solo
    información de localización: dirección, ciudad, etc.
    """

    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="sucursales")
    nombre_sucursal = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ciudad", "nombre_sucursal"]
        verbose_name_plural = "sucursales"

    def __str__(self):
        return f"{self.nombre_sucursal} - {self.ciudad}"