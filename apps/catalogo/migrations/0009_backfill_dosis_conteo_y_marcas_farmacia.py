from django.db import migrations

from apps.catalogo.utils import (
    detectar_marca,
    extraer_cantidad_normalizada,
    extraer_conteo_normalizado,
    extraer_dosis_normalizada,
    normalizar_nombre,
)


def backfill(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.all():
        nombre_normalizado = normalizar_nombre(producto.nombre)
        marca = detectar_marca(nombre_normalizado)
        cantidad = extraer_cantidad_normalizada(producto.nombre)
        dosis = extraer_dosis_normalizada(producto.nombre)
        conteo = extraer_conteo_normalizado(producto.nombre)
        if (
            producto.marca_normalizada != marca
            or producto.cantidad_normalizada != cantidad
            or producto.dosis_normalizada != dosis
            or producto.conteo_normalizado != conteo
        ):
            Producto.objects.filter(pk=producto.pk).update(
                marca_normalizada=marca,
                cantidad_normalizada=cantidad,
                dosis_normalizada=dosis,
                conteo_normalizado=conteo,
            )


def revertir(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Producto.objects.update(dosis_normalizada="", conteo_normalizado="")


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0008_producto_conteo_normalizado_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, revertir),
    ]
