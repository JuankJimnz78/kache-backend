from django.db import migrations

from apps.catalogo.utils import normalizar_nombre


def backfill(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.all():
        nuevo_valor = normalizar_nombre(producto.nombre)
        if producto.nombre_normalizado != nuevo_valor:
            Producto.objects.filter(pk=producto.pk).update(nombre_normalizado=nuevo_valor)


def revertir(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Producto.objects.update(nombre_normalizado="")


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0003_producto_nombre_normalizado'),
    ]

    operations = [
        migrations.RunPython(backfill, revertir),
    ]
