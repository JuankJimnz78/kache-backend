from django.db import migrations

from apps.catalogo.utils import detectar_marca, extraer_cantidad_normalizada, normalizar_nombre


def backfill(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.all():
        nombre_normalizado = normalizar_nombre(producto.nombre)
        marca = detectar_marca(nombre_normalizado)
        cantidad = extraer_cantidad_normalizada(producto.nombre)
        if producto.marca_normalizada != marca or producto.cantidad_normalizada != cantidad:
            Producto.objects.filter(pk=producto.pk).update(
                marca_normalizada=marca, cantidad_normalizada=cantidad
            )


def revertir(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Producto.objects.update(marca_normalizada="", cantidad_normalizada="")


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0005_producto_cantidad_normalizada_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, revertir),
    ]
