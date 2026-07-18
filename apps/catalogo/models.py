from django.db import models

from .utils import (
    detectar_marca,
    extraer_cantidad_normalizada,
    extraer_conteo_normalizado,
    extraer_dosis_normalizada,
    normalizar_nombre,
)


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
    marca = models.CharField(max_length=100, blank=True, default="")
    codigo_barras = models.CharField(max_length=50, blank=True, null=True, unique=True)
    imagen_url = models.URLField(blank=True, null=True, max_length=500)
    descripcion = models.TextField(blank=True, default="")
    unidad_medida = models.CharField(max_length=30, help_text="Ej: 1L, 500g, unidad")
    nombre_normalizado = models.CharField(
        max_length=200,
        blank=True,
        default="",
        db_index=True,
        help_text="Nombre normalizado (sin tildes/mayúsculas) usado para emparejar el mismo producto entre comercios. Se calcula solo, no editar a mano.",
    )
    marca_normalizada = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Marca conocida detectada en el nombre (ver MARCAS_CONOCIDAS), usada junto a cantidad_normalizada como criterio de matching cuando el nombre completo no coincide entre comercios. Se calcula solo.",
    )
    cantidad_normalizada = models.CharField(
        max_length=30,
        blank=True,
        default="",
        db_index=True,
        help_text="Presentación (volumen o peso) extraída del nombre en unidad canónica, ej. 'volumen:1000' o 'peso:2000'. Se calcula solo.",
    )
    dosis_normalizada = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Dosis por unidad (mg/gr, normalizada a mg) extraída del nombre, ej. '500' o '37.5+325' si es combinada. Usada junto a conteo_normalizado para el matching de farmacia. Se calcula solo.",
    )
    conteo_normalizado = models.CharField(
        max_length=10,
        blank=True,
        default="",
        db_index=True,
        help_text="Cuántas unidades trae el empaque (de patrones tipo 'x24', 'C/50'), extraída del nombre. Se calcula solo.",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.marca})" if self.marca else self.nombre

    def save(self, *args, **kwargs):
        self.nombre_normalizado = normalizar_nombre(self.nombre)
        self.marca_normalizada = detectar_marca(self.nombre_normalizado)
        self.cantidad_normalizada = extraer_cantidad_normalizada(self.nombre)
        self.dosis_normalizada = extraer_dosis_normalizada(self.nombre)
        self.conteo_normalizado = extraer_conteo_normalizado(self.nombre)
        super().save(*args, **kwargs)
