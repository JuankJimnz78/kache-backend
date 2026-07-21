import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import Comercio

_MEDIA_ROOT = tempfile.mkdtemp(prefix="kache_test_media_")

# Storage local (no R2 real) para probar la sincronización logo -> logo_url
# sin depender de credenciales de R2. El backend real (S3Storage hacia R2)
# se configura en settings.STORAGES y no se toca acá.
_LOCAL_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_LOCAL_STORAGES, MEDIA_ROOT=_MEDIA_ROOT)
class ComercioLogoSyncTests(TestCase):
    """
    Prueba el mecanismo de Comercio.save() que deriva logo_url a partir del
    campo logo (ver apps/comercios/models.py). Usa storage local en vez de
    R2 real -- lo que se valida es que el ORM sincroniza los dos campos
    correctamente, no la conectividad con R2 en sí (eso requiere
    credenciales reales, ver conversación).
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def _imagen_falsa(self, nombre="logo.png"):
        contenido_png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
            b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile(nombre, contenido_png_1x1, content_type="image/png")

    def test_logo_url_se_deriva_del_logo_al_guardar(self):
        comercio = Comercio.objects.create(
            nombre="Comercio de Prueba", tipo=Comercio.TIPO_SUPERMERCADO,
        )
        self.assertIsNone(comercio.logo_url)

        comercio.logo = self._imagen_falsa()
        comercio.save()

        comercio.refresh_from_db()
        self.assertTrue(comercio.logo)
        self.assertTrue(comercio.logo_url)
        self.assertEqual(comercio.logo_url, comercio.logo.url)

    def test_sin_logo_no_toca_logo_url(self):
        comercio = Comercio.objects.create(
            nombre="Comercio Sin Logo", tipo=Comercio.TIPO_FARMACIA,
            logo_url="https://ejemplo.com/legacy-logo.png",
        )
        comercio.nombre = "Comercio Sin Logo Renombrado"
        comercio.save()

        comercio.refresh_from_db()
        self.assertEqual(comercio.logo_url, "https://ejemplo.com/legacy-logo.png")
