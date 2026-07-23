  # Documentación técnica — Kache / PreciosEC Backend

  >Este backend fue diseñado para servir tanto a la aplicación móvil previa 
en Flutter como a la aplicación web construida en este proyecto — el mismo 
contrato de API sirve a ambas, lo cual reforzó desde el diseño del backend 
la idea de que la funcionalidad debe ser una sola, independiente del cliente 
que la consuma.

  ### Stack

  - **Django 5/6** + **Django REST Framework**, Python ≥3.11, gestionado con **uv** (no pip/poetry).
  - **PostgreSQL** como base de datos.
  - **JWT** (`rest_framework_simplejwt`) como mecanismo de auth principal, con **Google OAuth**
    como alternativa (ver [§3.5](#35-login-con-google-oauth)).
  - **Cloudflare R2** (API compatible con S3) para almacenamiento de imágenes, vía
    `django-storages` (ver [§3.6](#36-conexión-con-cloudflare-r2-y-subida-de-imágenes-desde-el-admin)).
  - **Playwright** + `requests`/`BeautifulSoup4` para los scrapers (cada sitio usa lo que
    realmente funciona contra él — ver [§3.1](#31-scrapers-y-normalizaciónmatching-de-productos)).
  - CI/CD con **GitHub Actions** (`.github/workflows/deploy.yml`): en cada push a
    `main`/`master` corre `manage.py test` contra un Postgres de servicio, y si pasa,
    hace deploy por SSH a un droplet: `git reset --hard`, `uv sync --frozen`,
    `migrate`, `collectstatic --clear`, reinicio de `gunicorn` + `nginx` vía `systemctl`,
    y un `curl` de salud contra `/admin/`.

  ### Capas / organización

  El proyecto está dividido en **apps Django** bajo `apps/`. No todas están igual de
  "vivas": hay un núcleo activo (el comparador de precios real) y un resto de apps que
  parecen venir de un scaffold previo genérico y no están conectadas al flujo principal:

  | App | Rol | Estado |
  |---|---|---|
  | `apps.catalogo` | `Producto` y `Categoria` — el corazón del catálogo, incluye toda la lógica de normalización/matching (`utils.py`) | **Activa**, foco principal de este trabajo |
  | `apps.comercios` | `Comercio` (las 6 cadenas) y `Sucursal` | **Activa** |
  | `apps.precios` | `Precio` (precio vigente por producto+comercio) e `HistorialPrecio` | **Activa** |
  | `apps.comparador` | `ListaComparacion` / `ItemComparacion` — listas de comparación del usuario | **Activa** |
  | `apps.extras` | Favoritos, alertas de precio, notificaciones, reseñas, reportes de producto, publicidad | **Activa** |
  | `apps.users` | Usuario custom (`AbstractUser` + email único), login/registro/JWT/reset de password, y ahora login con Google | **Activa** |
  | `apps.scraper` | Los 6 management commands de scraping (`scrapear_coral.py`, etc.) | **Activa** |
  | `apps.categories`, `apps.products`, `apps.orders`, `apps.emails` | Modelos genéricos de e-commerce (`Category`, `Product` con `price`/`stock`/IVA, `Order`) sin relación con `catalogo`/`comercios`/`precios` | **Presentes en `INSTALLED_APPS` pero no usados por el flujo de comparación de precios** — parecen residuo de un scaffold inicial. No los toqué ni los until este trabajo salvo para confirmar que no eran el archivo que un pedido específico buscaba (ver [§6](#6-limitaciones-conocidas-y-trabajo-pendiente)) |

  ### Patrón general en las vistas

  Las vistas de la API activa siguen un patrón consistente (`generics.ListCreateAPIView` /
  `RetrieveUpdateDestroyAPIView` de DRF), con `get_permissions()` diferenciando lectura
  pública (`AllowAny`) de escritura (`IsAdminUser` o `IsAuthenticated` según el recurso), y
  `get_serializer_class()` separando serializers de **lectura** (anidados, con campos
  calculados) de serializers de **escritura** ("RequestSerializer", con la lista mínima de
  campos editables). Este patrón es importante porque varias veces la causa de un bug fue
  **la ausencia de un mixin/clase esperada**, no lógica custom rota (ver [§4](#4-bugs-reales-encontrados-causa-raíz-y-por-qué-se-resolvieron-así)).

  ---

  ## 2. Cronología real de los bloques de trabajo

  En el orden real en que ocurrieron en esta sesión (no reordenado por tema):

  1. **Auditoría de un trabajo ya hecho** — normalización de nombres de producto, matching
    entre comercios, y reescritura de los 6 scrapers. Se pidió un informe de lo ya
    implementado, no implementación nueva.
  2. **Revisión de los "matches sospechosos"** — análisis caso por caso de 6 fusiones de
    producto con precios muy dispares entre comercios, para juzgar cuáles eran fusiones
    incorrectas.
  3. **Evaluación de riesgo de un ajuste al matching**, con una consulta real a la base de
    datos local para fundamentar la respuesta antes de tocar código.
  4. **Implementación del ajuste de matching** (`comparten_palabra_clave`) — con un bug real
    encontrado por un test propio antes de reportar éxito (ver [§4.1](#41-comparten_palabra_clave-una-palabra-vacía-cuela-el-match)).
  5. **Consulta sobre jerarquía de categorías** (Supermercados/Farmacias/Ferreterías) —
    terminó en **investigación de entorno, sin ningún cambio aplicado** (ver [§5.1](#51-jerarquía-de-categorías-8910-no-se-llegó-a-aplicar)).
  6. **Login con Google (OAuth)** — nuevo endpoint `POST /api/auth/google/`.
  7. Archivo de prueba (`test-google.html`) para generar un `id_token` real de Google sin
    necesidad de backend adicional.
  8. **Conexión con Cloudflare R2 + campo `logo` en `Comercio`** — con un bug real de timing
    encontrado por un test (ver [§4.2](#42-comerciosave-logourl-se-sincronizaba-antes-de-que-el-archivo-tuviera-su-nombre-final)),
    y una decisión de diseño explícita (Opción A vs B).
  9. **Personalización visual del Django Admin (ronda 1)** — `site_header`, CSS de marca
    (header + botones), plantilla `base_site.html`.
  10. **Diagnóstico pre-despliegue** (solo lectura, sin cambios de código) — confirmación de
      migraciones, inventario de archivos, nombres de variables de entorno.
  11. **Fix del 405 en `PATCH`/`PUT` de `ListaComparacion`** — causa raíz identificada antes
      de tocar nada, por pedido explícito del usuario.
  12. **Personalización visual del Django Admin (ronda 2)** — link "Ver sitio", favicon con
      colores reales de marca, color de links.

  ---

  ## 3. Detalle por bloque: qué, por qué, alternativas, y cómo se verificó

  ### 3.1. Scrapers y normalización/matching de productos

  **Qué se hizo** (confirmado leyendo el código real, no de memoria):

  - `apps/catalogo/utils.py` centraliza toda la normalización:
    `normalizar_nombre` (minúsculas, sin tildes, espacios colapsados),
    `detectar_marca` (contra una lista `MARCAS_CONOCIDAS` curada a mano),
    `extraer_cantidad_normalizada` (volumen/peso a unidad canónica ml/g),
    `extraer_dosis_normalizada` / `extraer_conteo_normalizado` (específico de farmacia:
    mg por unidad y unidades por caja, deliberadamente **no** mezclado con volumen/peso).
  - `Producto.save()` calcula estos 5 campos (`nombre_normalizado`, `marca_normalizada`,
    `cantidad_normalizada`, `dosis_normalizada`, `conteo_normalizado`) en cada guardado.
  - Los 6 scrapers (`scrapear_coral.py`, `scrapear_supermaxi.py`, `scrapear_fybeca.py`,
    `scrapear_cruzazul.py`, `scrapear_kywi.py`, `scrapear_ferrisariato.py`) buscan producto
    existente en cascada: `codigo_barras` exacto → `nombre_normalizado` exacto →
    `marca_normalizada` + (`dosis`+`conteo` en farmacia, o `cantidad_normalizada` en el
    resto), siempre excluyendo productos que ya tienen `Precio` en el mismo comercio (para
    no fusionar dos productos distintos del mismo catálogo que comparten marca+cantidad).
  - **Por qué esta cascada y no un único criterio**: `codigo_barras` es el más confiable
    pero rara vez está poblado igual en todos los sitios; `nombre_normalizado` exacto
    captura el caso (común, según los propios comentarios del código) de que dos
    retailers usan literalmente la descripción de fabricante; marca+cantidad es el
    *fallback* más débil y el que generó los falsos positivos documentados en
    [§3.3](#33-ajuste-al-matching-por-marcacantidad-comparten_palabra_clave).
  - **Fybeca se reescribió por completo**: el scraper viejo apuntaba a una API de VTEX que
    ya no existe (el sitio migró a Salesforce Commerce Cloud/Demandware). El nuevo usa el
    endpoint HTML `Search-UpdateGrid` (paginado, sin sesión ni JS) parseado con
    BeautifulSoup — **ya no necesita Playwright** para este sitio en particular.
  - **Supermaxi**: se le agregó paginación (`MAX_PAGINAS_POR_CATEGORIA=5`); antes solo leía
    la página 1 de cada categoría.
  - Se agregaron dos management commands de **auditoría, de solo lectura** (no modifican la
    base): `detectar_duplicados_producto` (agrupa productos existentes por unión
    transitiva usando los mismos 3 criterios que los scrapers, para ver si hay duplicados
    no fusionados) y `revisar_matches_sospechosos` (de los productos ya fusionados con 2+
    precios, marca los que tienen >20% de diferencia entre comercios como posible falso
    positivo).

  **Verificación real** (no solo "corrí y anduvo"):

  - `reporte_duplicados_producto.txt`: **0 grupos duplicados sobre 1067 productos** — el
    matching no generaba falsos negativos evidentes en el estado de la base al momento.
  - `reporte_matches_sospechosos.txt`: **6 de 16** productos con 2+ precio marcados por
    encima del umbral de 20% de diferencia — analizados uno por uno en el bloque 2 (ver
    abajo).

  > Nota de honestidad: la reescritura original de los 3 scrapers existentes y la creación
  > de los 3 nuevos **no la hice yo en esta ventana de contexto** — cuando empezó esta
  > sesión, ese trabajo ya estaba hecho (el primer pedido fue "dame un informe de los
  > cambios", sobre un `git diff` que ya existía). Lo que describo arriba lo confirmé
  > leyendo el código y los reportes reales, no lo estoy reconstruyendo de memoria de haber
  > escrito.

  ### 3.2. Revisión de los 6 "matches sospechosos"

  Se analizó cada uno de los 6 casos por encima del umbral de 20%, con veredicto y
  justificación basados en patrones de nombre/precio (no solo "se ve raro"):

  | Producto | Comercios / precios | Veredicto |
  |---|---|---|
  | Pintura Cóndor "para canchas"/Bucanero, 1gl | Ferrisariato \$17.05 vs Kywi \$26.77 (57%) | **Falso positivo, alta confianza** — "Base UI" sugiere base de tinturado, no un producto terminado |
  | Arroz Real 5kg | Supermaxi \$7.02 vs Coral \$10.38 (48%) | Sospechoso — el propio scraper de Coral ya advertía que "Arroz Real" vs "Arroz Real Viejo" no deben fusionarse solo por marca+peso |
  | Aceite spray Ecolove 180ml | Coral \$6.09 vs Supermaxi \$7.96 (31%) | Probablemente legítimo — mismo patrón de markup que otros aceites no-sospechosos del mismo reporte |
  | Arroz Casa del Arroz 5kg | Supermaxi \$5.38 vs Coral \$6.70 (25%) | Sospechoso — mismo patrón anómalo que el caso anterior, ambos justo en la presentación de 5kg |
  | Sellamur/Pintuco 1gl | Ferrisariato \$28.99 vs Kywi \$35.32 (22%) | **Falso positivo, alta confianza** — producto especializado (sellador), mismo patrón que el primero |
  | Esmalte Pinturas Unidas 1L | Kywi \$5.19 vs Ferrisariato \$6.30 (21%) | Sospechoso con duda genuina — ninguna pintura del reporte menciona color en el nombre, así que dos colores distintos podrían fusionarse bajo el mismo nombre genérico |

  Este análisis fue **puramente de lectura** — no se modificó ningún dato en este bloque.

  ### 3.3. Ajuste al matching por marca+cantidad (`comparten_palabra_clave`)

  **Decisión pedida por el usuario**: excluir la fusión por marca+cantidad cuando los dos
  nombres no comparten ninguna palabra más allá de marca/cantidad — acotado, sin excluir
  palabras genéricas de categoría (ej. "arroz", "pintura") a propósito, eso quedó fuera
  de alcance.

  **Verificación de riesgo antes de tocar código** (pedida explícitamente): se consultó la
  base real para listar todos los grupos `marca_normalizada+cantidad_normalizada` con 2+
  productos, y se comprobó a mano, con nombres reales, que la regla no rompería ningún
  match ya funcionando (ej. `Latex Condor Costa Blanco` vs `Pintura...Bucanero...CONDOR`
  no comparten ninguna palabra significativa → correctamente bloqueado).

  **Implementación**: `comparten_palabra_clave(nombre_a, nombre_b, marca)` en
  `apps/catalogo/utils.py`, aplicada en el fallback de marca+cantidad de los 6 scrapers
  (no se tocó la rama de dosis+conteo de farmacia).

  **Alternativa descartada**: excluir palabras genéricas de categoría además de
  marca/unidad — se decidió explícitamente NO hacerlo (fuera de alcance pedido), aunque
  esto significa que 2 de los 4 casos sospechosos identificados (arroz, pinturas unidas)
  **no quedan resueltos por este ajuste**, porque comparten una palabra genérica ("arroz",
  "brillante") que cuenta como "palabra en común" bajo la regla literal pedida.

  **Verificación real**: 6 tests unitarios en `apps/catalogo/tests.py`
  (`CompartenPalabraClaveTests`), corridos con `manage.py test apps.catalogo` — resultado
  `OK`.

  ### 3.4. Jerarquía de categorías 8/9/10 — no se llegó a aplicar

  Ver [§5.1](#51-jerarquía-de-categorías-8910-no-se-llegó-a-aplicar) — este bloque quedó en estado de
  investigación, sin ningún cambio de código ni de datos.

  ### 3.5. Login con Google (OAuth)

  **Qué se hizo**: nuevo endpoint `POST /api/auth/google/` (`apps/users/views.py`,
  `urls_auth.py`) que recibe `{"id_token": "..."}`, lo valida contra los servidores de
  Google con `google.oauth2.id_token.verify_oauth2_token()` usando `GOOGLE_CLIENT_ID`
  (leído de `.env`, no hardcodeado), y:
  - si ya existe un `User` con ese email, lo reutiliza (no duplica cuentas de quien ya se
    registró con password);
  - si no existe, lo crea con `set_unusable_password()` (no puede loguear con password) y
    un username generado del local-part del email, con desambiguación si ya existe.
  - Responde exactamente el mismo formato que `/auth/login/` (`access`, `refresh`,
    `user_id`, `username`, `email`, `is_staff`) para no forzar al frontend a manejar un
    formato distinto.

  **Dependencia nueva**: `google-auth` (agregada con `uv add`, no con pip suelto).

  **Verificación real**: se levantó el servidor de desarrollo local y se probó con `curl`:
  - `id_token` vacío → `400` con el error de validación del serializer.
  - `id_token` inválido (string arbitrario) → `401 "Token de Google inválido o expirado."`
  - Ningún caso devolvió `500`.

  **Alcance explícitamente no cubierto**: el payload de Google trae `picture` (foto), pero
  el modelo `User` no tiene ningún campo para guardarla — no se agregó porque no se pidió
  explícitamente.

  ### 3.6. Conexión con Cloudflare R2 y subida de imágenes desde el Admin

  **Decisión de diseño — Opción A vs B**: se planteaban dos formas de resolver la subida
  del logo de cada comercio:
  - **Opción A (elegida)**: campo `logo` (`ImageField`) nuevo en `Comercio`, separado del
    `logo_url` (texto) que ya existía; `logo_url` se deriva automáticamente de `logo` en
    `save()`.
  - **Opción B (descartada)**: mantener solo `logo_url` como texto, y montar en el admin un
    widget de subida manual que suba el archivo a R2 "a mano" y escriba la URL resultante.
  - **Por qué A**: reutiliza el manejo de storage de Django tal cual está diseñado (el
    widget de subida de `ImageField` en el admin viene gratis, con preview), en vez de
    reinventar esa lógica a mano.

  **Qué se hizo**:
  - `uv add django-storages boto3` (agregado a `pyproject.toml` + `uv.lock` juntos, para no
    repetir un problema anterior del proyecto donde `gunicorn` quedó instalado pero no
    reflejado en `pyproject.toml`).
  - `config/settings.py`: `STORAGES["default"]` → `storages.backends.s3.S3Storage`, leyendo
    `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_ENDPOINT_URL` / `R2_BUCKET_NAME` /
    `R2_PUBLIC_URL` del `.env` (con `default=""` para que un entorno sin esas variables no
    rompa al arrancar).
  - `apps/comercios/models.py`: campo `logo` + `save()` override que deriva `logo_url`.
  - `apps/comercios/admin.py`: preview del logo (miniatura) en lista y formulario;
    `logo_url` quedó de solo lectura (se deriva sola).
  - Migración `0003_comercio_logo_alter_comercio_logo_url.py` — aditiva, sin pérdida de
    datos (confirmado leyendo el archivo de migración).

  **Verificación real**:
  - `manage.py check` sin errores, incluso sin credenciales de R2 en el `.env` local (falla
    recién al intentar subir un archivo real, no al arrancar).
  - 2 tests en `apps/comercios/tests.py` usando un storage local (no R2 real) para validar
    la sincronización `logo` → `logo_url` sin depender de credenciales — ver el bug real
    encontrado en [§4.2](#42-comerciosave-logourl-se-sincronizaba-antes-de-que-el-archivo-tuviera-su-nombre-final).
  - Smoke test del admin real con un login de staff (test client de Django): changelist y
    formulario de `Comercio` devuelven `200`, `/api/kache/comercios/` sigue respondiendo
    igual que antes.
  - Confirmé en runtime que las 5 variables de entorno se leen con contenido real (sin
    imprimir los valores), y que los nombres coinciden carácter por carácter entre
    `settings.py` y el `.env` real del usuario (pedido explícito en el bloque de
    diagnóstico, [§3.7](#37-diagnóstico-pre-despliegue-solo-lectura)).

  **No se llegó a probar**: la subida real de los 6 logos contra R2 real ni la verificación
  por `curl` de que `logo_url` trae una URL real de R2 — quedó pendiente de que el usuario
  decida cómo (ver [§6](#6-limitaciones-conocidas-y-trabajo-pendiente)).

  ### 3.7. Diagnóstico pre-despliegue (solo lectura)

  Bloque explícitamente de "no toques nada, solo confirmá". Se confirmó:
  - El campo `logo` es un `ImageField` nuevo, separado de `logo_url` (no una reutilización
    del campo existente).
  - La migración `0003_comercio_logo_alter_comercio_logo_url.py` existe y es aditiva.
  - Inventario completo de archivos modificados/creados (6 modificados, 4 nuevos).
  - Los 5 nombres de variable de entorno R2 coinciden exactamente entre `.env` y
    `settings.py` — no había typos.
  - `makemigrations --check --dry-run` → `No changes detected` (nada quedó sin migrar).
  - `.env` está en `.gitignore` — sin riesgo de commitear credenciales.
  - Nota aparte encontrada de pasada: `test-google.html` (del bloque 3.5) ya estaba
    commiteado en el historial — no es parte del trabajo de R2, pero viaja al deploy si no
    se saca; no es un riesgo de seguridad (el Client ID de Google es público por diseño),
    pero es un archivo de prueba suelto en la raíz del repo.

  ### 3.8. Fix del 405 en PATCH/PUT de `ListaComparacion`

  **Causa raíz exacta** (confirmada leyendo el código, no supuesta): `ListaComparacionDetailView`
  heredaba de `generics.RetrieveDestroyAPIView` — combina `RetrieveModelMixin` +
  `DestroyModelMixin`, **sin `UpdateModelMixin`**. No había ningún `http_method_names`
  explícito en todo el repo (confirmado por grep) — la clase simplemente no tenía
  `update()`/`partial_update()` definidos, por eso PATCH/PUT caían en
  `http_method_not_allowed()` mientras que DELETE (que sí tiene mixin) funcionaba.

  El serializer **no era la causa** y de hecho ya era seguro por diseño: `usuario` ni
  siquiera está en la lista de `fields` de `ListaComparacionSerializer`, así que no había
  forma de cambiar el dueño de la lista vía este serializer aunque el cliente lo mandara;
  `items`/`id_lista`/`totales_por_comercio`/`fecha_creacion` ya eran de solo lectura
  (explícito o implícito por `auto_now_add`).

  **Fix**: un solo cambio de una línea — `RetrieveDestroyAPIView` →
  `RetrieveUpdateDestroyAPIView`. No hizo falta tocar el serializer.

  **Verificación real con curl** (usuario y lista de prueba creados y luego eliminados):
  - `PATCH {"nombre": "Nueva lista renombrada"}` → `200`, nombre actualizado.
  - `PATCH {"nombre": "Otro nombre", "usuario": 999, "items": [...]}` → `200`, pero
    `usuario`/`items` se ignoraron silenciosamente — confirmado con un `GET` posterior.
  - `DELETE` sigue funcionando (`204`).
  - Suite completa: 8/8 tests OK.

  ### 3.9. Personalización del Django Admin (dos rondas)

  **Ronda 1**:
  - `admin.site.site_header`/`site_title`/`index_title` en `config/urls.py`.
  - `static/admin/css/custom_admin.css`: en vez de forzar selectores con `!important`, se
    sobreescriben las **CSS custom properties** que Django Admin ya usa internamente
    (confirmadas leyendo el `base.css` real instalado, no de memoria): `--secondary`
    (de la que dependen `#header` y los botones "Guardar y continuar editando"),
    `--default-button-bg` (el botón "Guardar" principal, que no se deriva de
    `--secondary`), y `--header-color` (texto del header). Se confirmó que
    `dark_mode.css` no redefine ninguna de las tres, así que el tema se mantiene en modo
    oscuro también.
  - `templates/admin/base_site.html`: extiende `admin/base.html` (**no**
    `admin/base_site.html`, para no crear recursión infinita), replicando exactamente los
    bloques `title`/`branding`/`nav-global` del original de Django 6.0.6 (leídos del
    paquete instalado), y agregando el `<link>` al CSS en `extrastyle`.
  - Hicieron falta dos ajustes de `settings.py` que no existían antes:
    `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` y
    `STATICFILES_DIRS = [BASE_DIR / "static"]`.

  **Ronda 2**:
  - **Link "Ver sitio"**: resultó ser un feature **nativo** de Django ya existente
    (`{{ site_url }}` en el bloque `userlinks` de `admin/base.html`) — solo hacía falta
    fijar `admin.site.site_url` y sobreescribir `userlinks` para agregar
    `target="_blank" rel="noopener"`.
  - **Favicon**: bloqueado inicialmente — el pedido original decía "revisá
    `comercio-brand.theme.ts`" para sacar la paleta de los rombos del logo, pero **ese
    archivo no existe en este repositorio** (es del frontend, al que no tengo acceso). Se
    preguntó al usuario, que dio los hex reales (3 familias de color, 6 tonos cada una).
    Se construyó un favicon SVG simple con **un tono representativo de cada familia**
    (`#FFB300` naranja, `#1976D2` azul, `#D32F2F` rojo) — se decidió no usar los 18 tonos
    completos porque a tamaño de favicon (16-32px) se verían borrosos/indistinguibles.
  - **Color de links**: se confirmó la variable real en el `base.css` instalado
    (`--link-fg`, **no** `--secondary` como en la ronda 1) antes de tocar el CSS. Detalle
    encontrado al revisar: a diferencia de `--secondary`/`--default-button-bg`,
    **`--link-fg` sí se redefine en `dark_mode.css`** (a un azul claro, por contraste
    contra fondo oscuro) — se decidió **no** forzar el navy en modo oscuro ahí, porque
    dejaría los links casi ilegibles sobre fondo casi negro.

  **Verificación real, ambas rondas**: en cada ronda se usó el test client de Django con un
  login de staff real para confirmar el HTML servido (`site_header`, link `Ver sitio` con
  `target="_blank"`, `<link rel="icon">`), y además se levantó el servidor de desarrollo
  real (`runserver`) para confirmar por HTTP que el CSS y el favicon se sirven con el
  contenido correcto (no solo que el archivo existe en disco). Se confirmó que
  `/admin/comercios/comercio/`, `/admin/catalogo/producto/` y
  `/admin/catalogo/categoria/` seguían respondiendo `200`, y que filtros/búsqueda del
  admin de `Producto` seguían funcionando. Suite completa: 8/8 tests OK en ambas rondas.

  ---

  ## 4. Bugs reales encontrados (causa raíz) y por qué se resolvieron así

  Estos dos son los únicos bugs que aparecieron **durante el desarrollo de este trabajo**
  (no bugs preexistentes que se investigaron, sino errores que yo mismo introduje al
  escribir código y que un test propio detectó antes de reportar éxito):

  ### 4.1. `comparten_palabra_clave`: una palabra vacía "cuela" el match

  **Síntoma**: el test `test_bloquea_pintuco_sellamur_vs_metaltec` fallaba —
  `comparten_palabra_clave("...SELLAMUR...", "...Metaltec...")` devolvía `True` cuando
  debía dar `False`.

  **Causa raíz**: la primera versión de la función tokenizaba los nombres y solo excluía
  tokens de marca y de unidades de medida — **no** excluía preposiciones/artículos/
  conjunciones. Ambos nombres contenían la palabra "en" ("...humedad **3 en 1**..." /
  "...Pintuco Metaltec **3 en 1**..."), y esa coincidencia trivial bastaba para que la
  función devolviera `True`.

  **Por qué se resolvió así**: se agregó un set pequeño de "palabras vacías" puramente
  gramaticales (`de, del, la, en, y, para, con, sin...`) — deliberadamente **distinto** de
  excluir "palabras genéricas de categoría" (que sí quedó fuera de alcance por pedido
  explícito). La distinción importa: "arroz" o "pintura" describen *qué es* el producto
  (se dejan, a propósito, contar como palabra en común); "en"/"de"/"y" no describen nada,
  son pegamento gramatical — excluirlas no es una expansión de alcance, es necesario para
  que la condición "comparten una palabra" tenga sentido en absoluto.

  ### 4.2. `Comercio.save()`: `logo_url` se sincronizaba antes de que el archivo tuviera su nombre final

  **Síntoma**: el test `test_logo_url_se_deriva_del_logo_al_guardar` fallaba con
  `'/media/logo.png' != '/media/comercios/logos/logo.png'`.

  **Causa raíz**: la primera versión de `save()` leía `self.logo.url` **antes** de llamar a
  `super().save()`, asumiendo que el archivo ya estaba subido a esa altura (como parecía
  sugerir el flujo del admin). Pero el `upload_to` (el prefijo `comercios/logos/` que arma
  el nombre final del archivo en storage) recién se resuelve **dentro** de
  `super().save()` — específicamente en `Field.pre_save()`, que es donde Django realmente
  llama a `storage.save()` con el nombre ya procesado. Antes de eso, `self.logo.name` es
  todavía el nombre crudo del archivo subido (`logo.png`, sin prefijo).

  **Por qué se resolvió así**: se invirtió el orden — primero `super().save()` (que resuelve
  el nombre final y sube el archivo), y solo después, si `logo_url` quedó desactualizado,
  se corrige con `type(self).objects.filter(pk=self.pk).update(logo_url=...)` (un
  `.update()` de queryset, no otro `.save()` del modelo, para no reentrar en el mismo
  método).

  ---

  ## 5. Decisiones que se revirtieron o cambiaron de rumbo en el camino

  ### 5.1. Jerarquía de categorías 8/9/10 — no se llegó a aplicar

  El usuario pidió crear 3 categorías padre (Supermercados/Farmacias/Ferreterías, ids 8/9/10
  esperados) y reasignar 7 categorías existentes, ejecutándolo "vía Django shell o un
  management command en el backend real... dame los comandos exactos". La investigación
  cambió el rumbo completo del plan:

  1. Se confirmó por `curl` contra la API real en producción que hoy existen exactamente
    las 7 categorías esperadas, ids 1-7 contiguos.
  2. Se descubrió que el `.env` **local** apunta a `DB_HOST=localhost` — una base de datos
    de desarrollo **completamente separada** de producción (se confirmó comparando los
    mismos 7 nombres de categoría con *distinto orden de ids* entre ambas bases: prueba de
    que no son la misma base, ni siquiera un espejo).
  3. Se confirmó que no hay acceso SSH al droplet ni token de admin de la API disponibles
    en esta sesión — **nada se pudo ejecutar contra producción**.
  4. Se descubrió, revisando el serializer, que la API **no permite fijar `id_categoria`
    manualmente** de todas formas (es de solo lectura) — pero como el rango de ids en
    producción está limpio (1-7 sin huecos), crear las 3 categorías nuevas en el orden
    correcto vía `POST` haría que el auto-increment las asigne naturalmente a 8/9/10, sin
    necesidad de forzar nada.

  **Resultado**: se entregaron los comandos `curl` exactos (`POST` x3 + `PATCH` x7) listos
  para que el usuario los corra con su propio token de admin, pero **se decidió no
  ejecutar nada** — el mensaje que preguntaba cómo proceder (correrlo yo mismo con
  credenciales que me diera el usuario, vs. que lo corra el usuario) fue rechazado por el
  usuario a mitad de camino, y la conversación siguió en otra dirección. **Este bloque
  quedó sin resolver**, no por elección técnica sino porque no se retomó.

  ### 5.2. R2 real: verificación end-to-end no se llegó a hacer

  De forma similar, después de implementar y probar la lógica de sincronización
  `logo`→`logo_url` contra un storage local (sin R2 real), se preguntó al usuario cómo
  quería hacer la prueba real (compartir credenciales de R2 para probar localmente, vs.
  que lo pruebe él mismo en el servidor ya desplegado) — esa pregunta también fue
  rechazada/interrumpida, y la conversación pasó al siguiente pedido (personalización del
  admin) sin resolver esta verificación. **La subida real de los 6 logos contra R2 y la
  confirmación por `curl` de que `logo_url` trae una URL real nunca se hizo.**

  ### 5.3. Dos pedidos que asumían archivos de otro repositorio

  Dos veces en esta sesión el usuario pidió tocar un archivo que resultó no existir en
  este repositorio backend: primero `producto-http.adapter.ts` (un adapter TypeScript de
  frontend), después `comercio-brand.theme.ts` (los colores de marca, también de
  frontend). En ambos casos se verificó la existencia del archivo **antes** de intentar
  editarlo (`find`/`grep` reales, no "no lo veo, raro") y se lo comunicó directamente en
  vez de adivinar contenido o rutas. En el segundo caso, el usuario proveyó los hex reales
  directamente en el chat y se pudo continuar; en el primero, quedó pendiente de que el
  usuario confirme la ruta del repo correcto (no se retomó en esta sesión).

  ---

  ## 6. Limitaciones conocidas y trabajo pendiente

  Siendo honesto sobre el estado real, no un estado ideal:

  - **Sin acceso a producción**: en ningún momento de esta sesión hubo acceso SSH al
    droplet, ni un token de admin de la API real, ni credenciales de R2 en el entorno
    local. Todo lo verificado con "resultado real" en este documento se verificó contra
    **la base de datos de desarrollo local** (`comparador_pre_db` en `localhost`) — se
    confirmó explícitamente que esta base **no es un espejo** de producción (mismos
    nombres de categoría, distinto orden de ids). Cualquier cosa que diga "verificado" en
    este documento debe leerse como "verificado en local", no "confirmado en producción".
  - **Jerarquía de categorías**: pendiente de aplicar, ver [§5.1](#51-jerarquía-de-categorías-8910-no-se-llegó-a-aplicar).
  - **Subida real de logos a R2**: pendiente, ver [§5.2](#52-r2-real-verificación-end-to-end-no-se-llegó-a-hacer). Los 6 comercios
    (Coral, Cruz Azul, Ferrisariato, Fybeca, Kywi, Supermaxi) siguen con `logo`/`logo_url`
    vacíos en la base local a la fecha de este documento.
  - **Cobertura de productos con comparación real entre comercios es chica**: según los
    propios reportes de auditoría, solo hay categorías puntuales por comercio (Aceites y
    Arroz para Supermaxi/Coral, Dolor y Fiebre / Vitaminas para las farmacias, Pinturas
    para las ferreterías) — no un catálogo amplio. De los productos que sí se cruzan entre
    comercios, 6 de 16 (37%) quedaron marcados como posible falso positivo de matching,
    y de esos, el ajuste implementado en esta sesión solo resuelve 2 de los 4 casos
    identificados como alta confianza (los otros 2 comparten una palabra de categoría
    genérica, lo cual quedó fuera de alcance a propósito).
  - **`apps/products`, `apps/orders`, `apps/categories`, `apps/emails`**: presentes en
    `INSTALLED_APPS` pero sin relación con el flujo real de comparación de precios — no se
    investigó si tienen algún uso real o son residuo de un scaffold. No se tocaron en este
    trabajo.
  - **`test-google.html`**: archivo de prueba manual (sin lógica de producción) que quedó
    commiteado en la raíz del repo — funcional pero no pensado para viajar a producción.
  - **No hay README con contenido real** (`README.md` es solo un título).
  - **No se investigó ni se tocó nada de frontend/UI** (adaptación a desktop, pantallas
    específicas, etc.) — esta sesión fue exclusivamente sobre este repositorio backend.
  - **No hubo capturas de pantalla de UI en esta sesión**: toda la verificación de este
    trabajo (incluida la personalización visual del admin) se hizo con `curl`, el test
    client de Django, y levantando el servidor de desarrollo real para pedidos HTTP
    puntuales — **nunca con un navegador real ni herramientas tipo Playwright/captura de
    pantalla**. Por eso este documento no tiene imágenes embebidas de "cómo se ve": no
    existen, y generarlas ahora sería fabricar evidencia que no se produjo durante el
    trabajo real.
    - Sí encontré, buscando en el sistema de archivos, capturas de pantalla reales
      (`auth-01-post-register.png`, `cat-05-detalle-producto.png`,
      `comp-04-listado-listas.png`, etc.) guardadas en el *scratchpad* de **otra sesión**,
      de **otro proyecto** (`d--from-comparador-precios`, probablemente el frontend). No
      tengo el contexto de conversación que las generó — no sé qué verificaron
      exactamente ni con qué resultado — así que, siguiendo la instrucción de no rellenar
      con suposiciones, **no las embebo ni les invento descripción**. Si son relevantes,
      están en:
      `C:\Users\Marcos\AppData\Local\Temp\claude\d--from-comparador-precios\c1b5bad1-fb70-4795-bfab-cfddb94c26d5\scratchpad\`.

  ---

  ## 7. Referencia rápida — archivos tocados en esta sesión

  Por bloque, los archivos efectivamente creados o modificados (confirmado con `git diff`/`git status`, no de memoria):

  - **Matching** (§3.3): `apps/catalogo/utils.py`, `apps/catalogo/tests.py`, los 6 scrapers en `apps/scraper/management/commands/`.
  - **Google OAuth** (§3.5): `config/settings.py`, `apps/users/serializers.py`, `apps/users/views.py`, `apps/users/urls_auth.py`, `.env`, `pyproject.toml`/`uv.lock`, `test-google.html`.
  - **R2 + logo** (§3.6): `config/settings.py`, `apps/comercios/models.py`, `apps/comercios/admin.py`, `apps/comercios/migrations/0003_comercio_logo_alter_comercio_logo_url.py`, `apps/comercios/tests.py`, `pyproject.toml`/`uv.lock`.
  - **Admin ronda 1** (§3.9): `config/urls.py`, `config/settings.py`, `static/admin/css/custom_admin.css`, `templates/admin/base_site.html`.
  - **Fix `ListaComparacion`** (§3.8): `apps/comparador/views.py` (una sola línea).
  - **Admin ronda 2** (§3.9): `config/urls.py`, `static/admin/css/custom_admin.css`, `templates/admin/base_site.html`, `static/admin/img/favicon.svg`.

  ## Nota de aclaración sobre el alcance de este documento

Este documento fue generado por una sesión de Claude Code con visibilidad 
limitada a lo que se le pidió directamente en su propia ventana de trabajo. 
Algunas tareas mencionadas como "pendientes" o "no verificadas" en este 
documento (por ejemplo, la subida real de los logos de comercio a 
Cloudflare R2 y su verificación en producción, o la aplicación de la 
jerarquía de categorías 8/9/10) se completaron efectivamente en otras 
sesiones de trabajo — realizadas por comandos directos vía SSH contra el 
servidor de producción y verificación externa, fuera del alcance que esta 
instancia particular pudo observar. Se mantiene la redacción original sin 
modificar por transparencia sobre lo que esa sesión pudo confirmar 
directamente, pero se deja esta aclaración para que no se lea como un 
pendiente real al día de hoy.
