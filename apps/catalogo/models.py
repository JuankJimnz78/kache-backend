from django.db import models


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    pais_origen = models.CharField(max_length=100, blank=True, default="")
    sitio_web = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "marcas"

    def __str__(self):
        return self.nombre


class Etiqueta(models.Model):
    """Tag descriptivo para productos (ej. 'sin gluten', 'importado', 'oferta')."""

    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "etiquetas"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """Categoría de producto. Soporta jerarquía (ej. Lácteos > Quesos) vía categoria_padre."""

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, default="")
    categoria_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategorias",
    )

    class Meta:
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """
    Producto genérico del catálogo de comparación (ej. 'Aceite La Favorita 1L').
    No tiene precio propio: el precio vive en apps.precios.Precio, uno por cada
    comercio donde se vende, porque ese es justamente el dato que se compara.
    """

    nombre = models.CharField(max_length=200)
    marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )
    codigo_barras = models.CharField(max_length=50, blank=True, null=True, unique=True)
    descripcion = models.TextField(blank=True, default="")
    unidad_medida = models.CharField(max_length=30, help_text="Ej: 1L, 500g, unidad")
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )
    etiquetas = models.ManyToManyField(
        Etiqueta,
        blank=True,
        related_name="productos",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.marca.nombre})" if self.marca else self.nombre
