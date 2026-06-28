from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    """Usuario personalizado — compatible con los DTOs de la app Android."""
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username


class BusquedaReciente(models.Model):
    """Registra cada búsqueda que hace un usuario para mostrar historial en la app."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="busquedas_recientes",
    )
    termino = models.CharField(max_length=200)
    num_resultados = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "búsqueda reciente"
        verbose_name_plural = "búsquedas recientes"

    def __str__(self):
        return f'"{self.termino}" — {self.usuario.username}'
