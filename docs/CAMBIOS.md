# Qué ha cambiado respecto a la versión de 2023

Este documento explica **cada cambio**, en qué archivo está y **por qué** se hizo, para que
puedas decidir si es lo que quieres. La versión original sigue en `C:\FitnessApp` sin tocar.

Índice:

1. [Lo que tienes que hacer tú (urgente)](#1-lo-que-tienes-que-hacer-tú-urgente)
2. [Decisiones que he tomado y deberías revisar](#2-decisiones-que-he-tomado-y-deberías-revisar)
3. [Seguridad](#3-seguridad)
4. [Dependencias e infraestructura](#4-dependencias-e-infraestructura)
5. [Bugs corregidos](#5-bugs-corregidos)
6. [Arquitectura del código](#6-arquitectura-del-código)
7. [Modelo de datos (MongoDB)](#7-modelo-de-datos-mongodb)
8. [Kafka: productor y consumidor](#8-kafka-productor-y-consumidor)
9. [Interfaz](#9-interfaz)
10. [Funciones nuevas](#10-funciones-nuevas)
11. [Lo que se ha eliminado](#11-lo-que-se-ha-eliminado)
12. [Tabla de equivalencias de rutas](#12-tabla-de-equivalencias-de-rutas)
13. [Cómo se ha comprobado que funciona](#13-cómo-se-ha-comprobado-que-funciona)

---

## 1. Lo que tienes que hacer tú (urgente)

> ⚠️ El repositorio original `github.com/sergioRomero10/FitnessApp` es **público** y contiene
> el *client secret* de Google OAuth (en `flask_app/main.py` y en `flask_app/client_secret.json`).

1. **Revoca ese secreto**: Google Cloud Console → *APIs y servicios* → *Credenciales* → abre el
   cliente OAuth antiguo → *Restablecer secreto* (o bórralo y crea uno nuevo). Mientras no lo
   hagas, cualquiera puede usarlo.
2. **Borrar el archivo no basta**: sigue en el historial de git. Opciones:
   - Lo más sencillo: pon el repo antiguo en **privado** (o archívalo) y sube esta versión nueva
     a un repositorio **nuevo**, cuyo historial empieza limpio.
   - Si quieres conservar el repo antiguo público, habría que reescribir el historial con
     `git filter-repo`. Una vez revocado el secreto, deja de ser peligroso.
3. El secreto también se usaba como `app.secret_key`, así que cualquiera podía falsificar
   cookies de sesión de la app antigua. En la nueva, `SECRET_KEY` es independiente y va en `.env`.

## 2. Decisiones que he tomado y deberías revisar

Son elecciones razonables, pero tuyas. Si alguna no te convence, se cambia.

| Decisión | Por qué | Alternativa |
|---|---|---|
| **Sigue siendo Flask** (versión 3.1) | Es la esencia del proyecto y lo que defendiste en el TFG. | FastAPI + frontend separado: más trabajo y otro proyecto distinto. |
| **Se mantiene Kafka** | Es lo que hace "multiservicio" el proyecto y es lo que más luce en un portfolio. | Quitarlo y cargar el CSV directamente (la web ya sabe hacerlo con `SEED_ON_START`). |
| **Interfaz en inglés** | La original ya estaba casi toda en inglés (menús, botones); solo gimnasios estaba en español. He unificado. | Pasarla toda a español: son solo textos de las plantillas. |
| **Modo invitado** ("Try it as a guest") | Quien entre desde tu portfolio no tiene por qué darte su cuenta de Google. Además Google, con la app en modo "Testing", solo deja entrar a los usuarios que añadas a mano. | Solo Google: `DEMO_MODE=false`. |
| **Los invitados se borran a los 7 días** | Para que la base de datos no crezca indefinidamente con visitas. MongoDB lo hace solo (índice TTL). | Cambiar `GUEST_TTL_DAYS`. |
| **Esquema de datos nuevo** (ver sección 7) | El antiguo tenía errores de diseño que causaban bugs. | — No hay migración automática; como es una demo, se empieza con la base de datos vacía. |
| **Solo se añaden a una dieta alimentos favoritos** | Es como funcionaba la original (el desplegable salía de tus favoritos). | Permitir buscar cualquier alimento en el formulario de la dieta. |
| **El código de normalización está duplicado** en `web/` y `pipeline/` | Son dos imágenes Docker independientes; compartir un paquete complicaría el build. Hay un test en cada lado con el mismo ejemplo para detectar si se desincronizan. | Crear un paquete común `shared/`. |

## 3. Seguridad

| Antes | Ahora | Dónde |
|---|---|---|
| Client secret de Google y `secret_key` escritos en el código y subidos a GitHub. | Todo se lee de variables de entorno (`.env`, que está en `.gitignore`). Si falta `SECRET_KEY`, la app **no arranca**. | `config.py`, `__init__.py`, `.gitignore` |
| `debug=True` en `0.0.0.0:80`: el depurador de Werkzeug permite ejecutar código en el servidor. | Gunicorn (servidor de producción), sin modo debug. | `web/Dockerfile` |
| `OAUTHLIB_INSECURE_TRANSPORT=1` (OAuth sin https). | Eliminado. Authlib + `ProxyFix` para que detrás de un proxy https las URLs sean https. | `blueprints/auth.py`, `__init__.py` |
| Un único objeto `Flow` global para todos los usuarios (se podían mezclar los `state` de dos logins). | Authlib guarda el estado en la sesión de cada usuario y valida `state`, `nonce` y la firma del token. | `blueprints/auth.py` |
| `credentials._id_token` (atributo privado) y `pip._vendor.cachecontrol` (código interno de pip). | API pública de Authlib. | `blueprints/auth.py` |
| Sin protección CSRF: otra web podía hacer que tu navegador añadiese/borrase dietas. | Flask-WTF `CSRFProtect` en todos los POST; el JS envía el token en la cabecera `X-CSRFToken`. | `__init__.py`, `forms.py`, plantillas, `app.js` |
| Logout por GET (un `<img src="/logout">` en cualquier web te desconectaba). | Logout por POST con CSRF. | `blueprints/auth.py`, `base.html` |
| MongoDB sin usuario ni contraseña y con el puerto 27017 abierto a la red. | Usuario root + usuario de la app con permisos **solo** sobre su base de datos. Puertos ligados a `127.0.0.1`. | `docker-compose.yml`, `mongo/init-app-user.js` |
| Cookies de sesión con la configuración por defecto. | `HttpOnly`, `SameSite=Lax`, `Secure` en producción; la sesión se regenera al iniciar sesión. | `config.py`, `auth.py` |
| Redirecciones con `?next=` sin validar. | Solo se permite redirigir a rutas de la propia web. | `auth.py` (`safe_next`) |
| Los contenedores se ejecutaban como root. | Usuario sin privilegios (`uid 10001`). | `Dockerfile`s |
| Cualquiera podía ver/borrar una dieta conociendo su nombre si compartía sesión. | Todas las consultas de dietas filtran por `user_id`: una dieta ajena devuelve 404. | `services/diets.py` |

## 4. Dependencias e infraestructura

| Pieza | 2023 | 2026 | Notas |
|---|---|---|---|
| Python | `python:3` (sin versión) y `3.9-slim-buster` | `python:3.13-slim` | 3.9 y Debian Buster ya no tienen soporte. |
| Gestor de dependencias | `requirements.txt` con 30+ paquetes a mano (uno en UTF-16, con paquetes que no tocaban: `google`, `flow`, `datetime`) | `pyproject.toml` + `uv.lock` | Solo se declaran las dependencias directas; `uv.lock` fija las versiones exactas de todo. |
| Flask / Werkzeug | 2.2.3 / 2.2.3 (con CVEs) | 3.1.x | |
| Login Google | `google-auth-oauthlib` + hacks | `authlib` | |
| Kafka (cliente) | `kafka-python 2.0.2` (no funciona en Python ≥ 3.12) | `confluent-kafka` | Cliente oficial de Confluent, basado en librdkafka. |
| Kafka (broker) | `wurstmeister/kafka` + ZooKeeper (abandonados) | `apache/kafka:4.1.0` en modo KRaft | Kafka 4 ya no usa ZooKeeper: un contenedor menos. |
| Panel de Kafka | Kafdrop (con flag `-noverify` que las JVM nuevas ya no aceptan) | `kafbat/kafka-ui` (opcional, perfil `tools`) | |
| MongoDB | `mongo:latest` | `mongo:8.0` | Versión fija: no cambia sola al reconstruir. |
| Servidor web | `app.run(debug=True)` | Gunicorn | |
| Arranque ordenado | `time.sleep(5/20/30)` en cada servicio | `healthcheck` + `depends_on: condition: service_healthy` | Cada servicio espera a que el anterior esté *de verdad* listo. |
| docker-compose | `version: '3'` (obsoleto) | Formato actual, sin `version` | |
| Bootstrap | Mezcla de 4.5, 4.6, 5.1 y 5.3-alpha | 5.3.3 en todas las páginas | |
| jQuery + DataTables 1.11 | Sí | Eliminados | La búsqueda y paginación ahora se hacen en el servidor. |
| FullCalendar | 6.1.8 | 6.1.15 | |
| Mapas | — | Leaflet 1.9.4 + OpenStreetMap | |
| Tests | Ninguno | pytest + ruff | 39 tests contra un MongoDB real desechable (`docker compose --profile test run --rm tests`). |
| CI | Ninguna | GitHub Actions: ruff + pytest + build | `.github/workflows/ci.yml` |

## 5. Bugs corregidos

| Bug en la versión original | Qué pasaba | Arreglo |
|---|---|---|
| `/delete_fav_food` por GET usaba `favs_foods` sin definir. | Error 500 (`NameError`). | Ruta separada `/favorites/remove`, solo POST. |
| `/add_food_menu` sin sesión no devolvía nada. | Error 500. | Todas las rutas privadas usan `@login_required`, que redirige al login. |
| `/show_diet` leía `request.form` también en GET. | Error 400 al recargar. | La dieta tiene su propia URL: `/diets/<id>`. |
| `int(request.form['quantity'])` sin validar. | Error 500 con texto, vacío o negativo. | `IntegerField` con rango 1–5000. |
| `insertuser` asignaba `id = count + 1`. | Ids repetidos al borrar usuarios o con dos altas a la vez. | El `_id` lo genera MongoDB. |
| `calculate_cals_food` devolvía un texto de error y luego se hacía `float()` sobre él. | Error 500 al ver una dieta con un alimento sin calorías. | Las calorías se calculan al vuelo desde el catálogo (números). |
| `conexionBD.py`: `replace_one({"Fooditem": ...})` (typo). | Nunca actualizaba nada. | Eliminado; el consumidor hace *upsert* por `key`. |
| Comparación que incluía `_id`. | Siempre detectaba "cambios". | Eliminado. |
| Alimentos con el mismo nombre en distintas categorías (p. ej. *Almonds*). | Uno sobrescribía al otro: de 2.225 filas solo quedaban ~1.990 alimentos (se perdían 232). | Clave única `categoría/nombre`. |
| `login_is_required` sin `functools.wraps` y llamando a `function()` sin argumentos. | Al decorar una segunda ruta, Flask fallaba al arrancar. | `login_required` con `@wraps` y `*args, **kwargs`. |
| Nombres de dieta usados como claves del documento. | Un nombre con `.` o `$` rompía el documento del usuario. | Las dietas son documentos propios; el nombre es un campo más. |
| Cada cambio hacía `$set` del usuario completo tras modificarlo en Python. | Dos peticiones a la vez → una pisaba a la otra. | Operaciones atómicas: `$addToSet`, `$pull`, `$push`, `$inc`. |
| Calorías de la dieta guardadas como texto (`"78.00"`). | Se quedaban desfasadas si cambiaba el catálogo. | Solo se guardan los gramos; las calorías se calculan al mostrar. |
| Búsqueda de gimnasios con la ciudad concatenada en la URL. | "Las Palmas" o un `&` rompían la búsqueda. | `params=` de requests (codifica el texto). |
| Nominatim sin User-Agent, sin timeout y con `/search.php`. | Va contra su política de uso (pueden bloquearte) y podía colgarse. | User-Agent, `timeout=10`, `/search`, caché de 1 h. |
| Se buscaba la palabra "gimnasio" en el nombre del sitio. | En Las Palmas de Gran Canaria salía **1** gimnasio. | Búsqueda por la categoría de OpenStreetMap `[leisure=fitness_centre]`: **29** en Las Palmas, 40 (el máximo) en Madrid. |
| El dataset tiene una fila repetida (*Raisin Bran Crunch*). | — | La carga elimina duplicados: 2.224 alimentos. |
| `gyms.html` mostraba `gym.address`, que nunca se rellenaba. | Dirección vacía. | Se separa nombre y dirección de `display_name`. |
| Calendario: el último día de la dieta no se pintaba. | En FullCalendar la fecha final es exclusiva. | Se suma un día al pintar. |
| La foto de Google en el navbar se cargaba dos veces (Jinja + jQuery). | Parpadeo; a veces fallaba. | Una sola `<img>` con `referrerpolicy` y respaldo. |
| La portada mandaba los ~2.200 alimentos en cada visita. | Página pesada y lenta. | Búsqueda y paginación en el servidor (25 por página) con índices. |
| Errores de conexión → redirección a `/protected_area`. | Bucle de redirecciones si Mongo caía. | Páginas de error 404/500 y `/healthz`. |
| `print()` por todas partes. | Sin niveles ni formato. | `logging`. |

## 6. Arquitectura del código

**Antes**: un `main.py` de 800 líneas con conexión a la BD, funciones de negocio y rutas
mezcladas, y la conexión a Mongo hecha al importar el módulo (con un `time.sleep(5)`).

**Ahora** (`web/fitnessapp/`):

- **App factory** (`create_app()` en `__init__.py`): crea la aplicación a partir de la
  configuración. Permite que los tests usen una base de datos en memoria.
- **Blueprints** (`blueprints/`): cada grupo de rutas en su archivo — `auth`, `foods`,
  `favorites`, `diets`, `gyms`, `main`. Las rutas solo validan la petición, llaman al
  servicio y eligen la plantilla.
- **Servicios** (`services/`): toda la lógica y el acceso a MongoDB. No saben nada de HTTP.
- **Formularios** (`forms.py`): validación en el servidor con WTForms.
- **Configuración** (`config.py`): solo variables de entorno.
- **Comando `flask seed`**: carga el CSV directamente, sin Kafka.

## 7. Modelo de datos (MongoDB)

Base de datos: `fitnessapp` (antes `CaloriasDB`).

**`foods`** (antes `CaloriasCollection`)

```js
// Antes                                   // Ahora
{                                          {
  FoodCategory: "cannedfruit",               key: "canned-fruit/applesauce",   // único
  FoodItem: "applesauce",                    name: "Applesauce",
  per100grams: "100g",                       name_lower: "applesauce",         // para buscar
  Cals_per100grams: "62 cal",   // texto     category: "Canned Fruit",
  KJ_per100grams: "260 kj",     // texto     unit: "g",
  RegisterDay: ISODate(...)                  kcal_per_100: 62,                 // número
}                                            kj_per_100: 260,
                                             created_at, updated_at
                                           }
```

**`users`** (antes `Users`)

```js
// Antes                                   // Ahora
{                                          {
  mail: "...",                               _id: ObjectId,           // lo genera Mongo
  id: 3,              // count()+1           google_sub: "1234...",   // id estable de Google
  favs_foods: ["apple"],                     email, name, picture,
  diet: {                                    favorites: ["fruits/apple"],
    "Cut": { num_diet, name, start_date,     is_guest: false,
             end_date, foods: [              expires_at: Date          // solo invitados (TTL)
               {name, quantity, cals:"52"}   }
    ]}
  }
}
```

**`diets`** (nueva colección; antes estaban dentro del usuario)

```js
{
  _id: ObjectId,
  user_id: ObjectId,              // dueño de la dieta
  name: "Cut",
  start_date: "2026-10-01",
  end_date: "2026-10-07",
  items: [{ key: "fruits/apple", grams: 150 }],
  expires_at: Date                // solo si el dueño es invitado
}
```

Índices: `foods.key` (único), `foods.name_lower`, `users.email` / `users.google_sub` (únicos),
`diets.user_id`, y TTL en `expires_at`. Se crean solos al arrancar (`db.py`).

## 8. Kafka: productor y consumidor

Ahora es **una sola imagen** (`pipeline/`) con dos comandos.

**Productor** (`fitness_pipeline/producer.py`)
- Crea el topic `foods.catalog` si no existe, reintentando hasta que Kafka responde (en vez
  de `time.sleep(20)`).
- Cada mensaje lleva como **clave** el identificador del alimento.
- Productor idempotente con `acks=all` y callback de entrega: si algo falla, el contenedor
  termina con error y se ve en `docker compose ps`.

**Consumidor** (`fitness_pipeline/consumer.py`)
- Procesa en lotes de 200 y escribe con `bulk_write` (una ida y vuelta a Mongo por lote).
- **Commit manual del offset después de escribir en Mongo**. Antes era automático: si el
  proceso caía entre leer y escribir, ese mensaje se perdía.
- Mensajes mal formados se registran y se saltan.
- Se detiene limpiamente con `docker compose stop`.

El archivo `ConexionBD/csv_to_kafka.py` original no se usaba (y escribía en otra base de
datos `CaloriasBD`); no se ha migrado.

## 9. Interfaz

Se ha mantenido la **identidad visual**: fondo oscuro, rojo `#de1425`, navbar con brillo rojo,
subrayado animado en el menú y el título **FITNESSAPP** con letras huecas que saltan al pasar
el ratón.

Cambios:
- **Bootstrap 5.3** con su tema oscuro nativo (antes 4 versiones mezcladas).
- Tipografías *Inter* (texto) y *Bebas Neue* (títulos).
- Tarjetas con bordes suaves, calorías en "pastillas" rojas, iconos de Bootstrap Icons.
- **Diseño adaptable a móvil**: columnas que se ocultan, menú plegable, calendario en modo
  lista en pantallas pequeñas.
- **Estrella de favoritos sin recargar la página** (con aviso tipo *toast*). Si el JavaScript
  falla, el formulario funciona igual recargando.
- Página de login rehecha (antes era la única con fondo claro y otro estilo).
- Avisos (*flash*) con colores según el tipo: éxito, aviso, error.
- Página **About** que explica la arquitectura (antes los enlaces "About us" y "Contact us"
  no llevaban a ninguna parte).
- Páginas de error 404/500 con el mismo estilo.
- Accesibilidad: `aria-label`, foco visible, `prefers-reduced-motion` desactiva animaciones.

## 10. Funciones nuevas

- **Buscador de alimentos** por nombre y filtro por categoría, con paginación.
- **kJ** además de kcal, y unidad correcta (g o ml).
- **Dietas**: página propia por dieta, editar nombre y fechas, borrar con confirmación, total
  de calorías destacado. Al añadir un alimento que ya está, se suman los gramos.
- **Calendario**: al pulsar una dieta se abre.
- **Gimnasios en un mapa** (Leaflet + OpenStreetMap); al pulsar uno en la lista, el mapa va a él.
- **Modo invitado** para probar la demo sin cuenta.
- `/healthz` para Docker y la plataforma de despliegue.

## 11. Lo que se ha eliminado

| Eliminado | Motivo |
|---|---|
| `main.py`, `templates/`, `Dockerfile` y `requirements.txt` de la raíz | Copia antigua de `flask_app/`. |
| `ConexionBD/` | No estaba en el docker-compose y tenía bugs; su función la hace el consumidor (o `flask seed`). |
| `client_secret.json` (×3) | Secretos fuera del repositorio. |
| ZooKeeper, Kafdrop | Kafka 4 no necesita ZooKeeper; Kafdrop sustituido por kafka-ui. |
| jQuery, DataTables, `script.js` | Búsqueda en el servidor; JS propio mínimo sin dependencias. |
| `index_with_session.html`, `sportcenters.html`, `resultado_busqueda.html` | No se usaban. |
| Variable `DAY_SIMULATION_INTERVAL_SECONDS` | No la leía nadie. |
| `.idea/`, `venv/` | No deben estar en el proyecto (ahora en `.gitignore`). |

## 12. Tabla de equivalencias de rutas

| Antes | Ahora |
|---|---|
| `/` y `/protected_area` | `/` (catálogo con búsqueda) |
| `/redirect_to_login`, `/login` | `/login` (página) · `/auth/google` · `/auth/guest` |
| `/callback` | `/auth/callback` |
| `/logout` (GET) | `/logout` (POST) |
| `/add_favorite` | `/favorites/toggle` |
| `/favorite_foods` | `/favorites/` |
| `/delete_fav_food` | `/favorites/remove` |
| `/create_diet`, `/add_to_diet`, `/show_options_diet` | `/diets/` (lista + crear) |
| `/show_diet` | `/diets/<id>` |
| `/add_food_menu`, `/add_food_to_diet` | `/diets/<id>/items` |
| `/delete_food_diet_web` | `/diets/<id>/items/remove` |
| — | `/diets/<id>/edit` |
| `/delete_diet` | `/diets/<id>/delete` |
| `/show_calendar` | `/diets/calendar` (+ `/diets/events.json`) |
| `/search_gyms` (POST) | `/gyms/?city=...` (GET, se puede compartir el enlace) |
| — | `/about`, `/healthz` |

## 13. Cómo se ha comprobado que funciona

Comprobado el 17/10/2026 en tu PC (Windows 11 + Docker Desktop 28.3):

| Comprobación | Resultado |
|---|---|
| `ruff check` y `ruff format --check` (web y pipeline) | Sin errores. |
| Tests web (`pytest`, MongoDB real) | 37 pasados. |
| Tests pipeline | 2 pasados. |
| `docker compose up --build` | Los 5 servicios arrancan en orden; web, MongoDB y Kafka quedan *healthy*. |
| Productor | Publica 2.225 filas en `foods.catalog`, 0 errores, y termina con código 0. |
| Consumidor | Guarda 2.224 alimentos en MongoDB (la fila repetida se fusiona). |
| Navegador: entrar como invitado, buscar «apple» (33 resultados), marcar 2 favoritos con la estrella sin recargar | OK, sin errores en la consola. |
| Crear dieta con nombre con tilde, añadir 250 g de *Apple Crisp* | Total 390 kcal (156 × 2,5). OK. |
| Calendario | La dieta del 19 al 25 se pinta incluyendo el día 25. |
| Gimnasios en Las Palmas de Gran Canaria (Nominatim real) | 29 resultados en el mapa. |
| Vista móvil (375 px) | Menú plegado, tabla compacta, sin scroll horizontal. |
| Panel kafka-ui (`--profile tools`) | Arranca en http://localhost:8080 y muestra el topic `foods.catalog`. |

**No comprobado**: el login con Google (necesita que crees credenciales nuevas) y el
despliegue en Render/Atlas (necesita tus cuentas). Los pasos están en [DESPLIEGUE.md](DESPLIEGUE.md).

**Convivencia con la versión original**: el proyecto de Docker se llama `fitnessapp2026`
para no mezclarse con los contenedores de `C:\FitnessApp` (que se llaman `fitnessapp-*`).
La web nueva usa el puerto 8000; la original usaba el 80, así que pueden funcionar a la vez.
