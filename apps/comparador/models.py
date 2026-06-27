from django.conf import settings
from django.db import models

from apps.catalogo.models import Producto
from apps.comercios.models import Comercio


class ListaComparacion(models.Model):
    """
    Una lista de comparación que el usuario va armando: para cada producto
    que agrega, elige en qué comercio lo compra. El resultado final se puede
    agrupar por comercio para ver cuánto pagaría en cada uno.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="listas_comparacion",
    )
    nombre = models.CharField(max_length=100, blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre or f"Lista de {self.usuario.username} ({self.fecha_creacion:%d/%m/%Y})"


class ItemComparacion(models.Model):
    """
    Un producto + el comercio elegido por el usuario para comprarlo, dentro
    de una ListaComparacion. precio_momento es una 'foto' del precio al
    momento de agregarlo — si el precio real cambia después, esta lista
    no cambia sola, para que el usuario no se confunda comparando contra
    un número que ya no es el que vio.
    """

    lista = models.ForeignKey(ListaComparacion, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    comercio = models.ForeignKey(Comercio, on_delete=models.CASCADE)
    precio_momento = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["comercio", "producto"]
        unique_together = ["lista", "producto"]

    def __str__(self):
        return f"{self.producto.nombre} -> {self.comercio.nombre} (lista #{self.lista_id})"