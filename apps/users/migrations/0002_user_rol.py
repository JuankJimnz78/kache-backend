# Generated manually — agrega el campo 'rol' (ADMIN/OPERADOR/CLIENTE) al modelo User.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrador'),
                    ('OPERADOR', 'Operador'),
                    ('CLIENTE', 'Cliente'),
                ],
                default='CLIENTE',
                max_length=20,
            ),
        ),
    ]
