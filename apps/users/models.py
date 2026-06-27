from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario personalizado — compatible con los DTOs de la app Android."""
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username
