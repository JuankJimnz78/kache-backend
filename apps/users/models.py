from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario personalizado — compatible con los DTOs de la app Android."""

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        OPERADOR = "OPERADOR", "Operador"
        CLIENTE = "CLIENTE", "Cliente"

    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CLIENTE)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username
