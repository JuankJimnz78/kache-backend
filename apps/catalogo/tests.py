from django.test import SimpleTestCase

from apps.catalogo.utils import comparten_palabra_clave, detectar_marca, normalizar_nombre


class CompartenPalabraClaveTests(SimpleTestCase):
    """
    Valida el filtro extra del fallback de matching marca+cantidad
    (apps/catalogo/utils.py): exigir que los nombres compartan alguna
    palabra más allá de marca y unidad, para no fusionar líneas de producto
    distintas que solo coinciden en esos dos campos.

    Los pares de "Latex Condor.../Bucanero..." y "Sellamur.../Metaltec..."
    son nombres reales encontrados en la base (grupos marca_normalizada +
    cantidad_normalizada con 2+ filas) -- ver informe de matches
    sospechosos. Los demás son representativos del patrón de redacción real
    visto en el catálogo (mismo producto descrito distinto entre sitios),
    ya que el nombre original del lado que sí quedó fusionado no se
    conserva en la base (solo sobrevive el nombre con el que se creó el
    Producto la primera vez).
    """

    def _comparten(self, nombre_a, nombre_b):
        norm_a = normalizar_nombre(nombre_a)
        norm_b = normalizar_nombre(nombre_b)
        marca = detectar_marca(norm_a) or detectar_marca(norm_b)
        return comparten_palabra_clave(norm_a, norm_b, marca)

    # ── Casos de alta confianza que deben quedar bloqueados ─────────────

    def test_bloquea_condor_pintura_canchas_vs_latex_costa(self):
        # Nombres reales de la DB (marca=condor, cantidad=volumen:3785).
        self.assertFalse(self._comparten(
            "Latex Condor Costa Blanco 1Gal",
            'Pintura en Base agua Bucanero para canchas Base UI 1 gl. - CONDOR',
        ))

    def test_bloquea_pintuco_sellamur_vs_metaltec(self):
        # Nombres reales de la DB (marca=pintuco, cantidad=volumen:3785).
        self.assertFalse(self._comparten(
            'Bloqueador de humedad 3 en 1 "SELLAMUR" en presentación de 1 gl. - PINTUCO',
            "Pintura Esmalte Pintuco Metaltec 3 en 1 - 1Gal - Varios Colores",
        ))

    def test_ignora_marca_y_unidad_como_palabra_compartida(self):
        # Solo comparten marca y unidad de medida, ninguna palabra
        # descriptiva -- confirma que marca/unidad no cuentan como clave.
        self.assertFalse(self._comparten(
            "Esmalte Sintetico Condor 1 Litro",
            "Anticorrosivo Condor 1 Litro",
        ))

    # ── No debe romper matches que hoy funcionan bien ───────────────────

    def test_permite_arroz_real_misma_categoria(self):
        # Nombres reales de la DB (marca=real, cantidad=peso:5000). Solo
        # comparten "arroz" -- bajo el alcance acordado (sin excluir
        # palabras genéricas de categoría), esto sigue fusionando.
        self.assertTrue(self._comparten(
            "Arroz Blanco REAL 5000 G",
            "Arroz Real 5 Kilos",
        ))

    def test_permite_mismo_aceite_redactado_distinto_entre_comercios(self):
        # Representativo del patrón real de nombres de aceite del catálogo:
        # mismo producto, dos formas de ordenar/redactar la misma
        # descripción -- deben seguir compartiendo palabras suficientes.
        self.assertTrue(self._comparten(
            "Aceite Comestible 50% Menos Grasa Saturada LA FAVORITA 900 Ml",
            "Aceite La Favorita Comestible Menos Grasa Saturada 900 Ml",
        ))

    def test_permite_misma_pintura_con_una_palabra_descriptiva_en_comun(self):
        # Alcanza con una sola palabra en común más allá de marca/unidad.
        self.assertTrue(self._comparten(
            "Pintura Latex Interior Blanco Condor 1 Galon",
            "Latex Interior Condor Mate 1Gal",
        ))
