from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.catalogo.models import Producto
from apps.comercios.models import Comercio


class Precio(models.Model):
    """
    Precio actual de un Producto en un Comercio (cadena, no sucursal).
    Es el dato central que Kache compara entre comercios.
    """

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="precios")
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="precios")
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    en_oferta = models.BooleanField(default=False)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["producto", "comercio"]
        ordering = ["producto", "comercio"]

    def __str__(self):
        return f"{self.producto.nombre} @ {self.comercio.nombre}: {self.precio_actual}"

    @property
    def precio_efectivo(self):
        """Precio que realmente paga el usuario: el de oferta si está activa, si no el normal."""
        if self.en_oferta and self.precio_oferta is not None:
            return self.precio_oferta
        return self.precio_actual


class HistorialPrecio(models.Model):
    """
    Snapshot de un precio en un momento dado. Se crea SOLO automáticamente
    (ver señal más abajo) cada vez que precio_actual de un Precio existente
    cambia — nunca se crea a mano, por eso no tiene endpoint de escritura.
    """

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="historial_precios")
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE, related_name="historial_precios")
    precio_registrado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_registro"]
        verbose_name_plural = "historial de precios"

    def __str__(self):
        return f"{self.producto.nombre} @ {self.comercio.nombre}: {self.precio_registrado}"


@receiver(pre_save, sender=Precio)
def registrar_historial_si_cambia_precio(sender, instance, **kwargs):
    """
    Se ejecuta justo ANTES de guardar un Precio. Si ya existía (es una
    actualización, no una creación) y el precio_actual cambió, guarda el
    precio ANTERIOR en HistorialPrecio antes de que se sobreescriba.
    """
    if not instance.pk:
        return  # precio nuevo: no hay precio anterior que registrar

    try:
        anterior = Precio.objects.get(pk=instance.pk)
    except Precio.DoesNotExist:
        return

    if anterior.precio_actual != instance.precio_actual:
        HistorialPrecio.objects.create(
            producto=anterior.producto,
            comercio=anterior.comercio,
            precio_registrado=anterior.precio_actual,
        )