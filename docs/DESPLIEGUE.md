# Desplegar FitnessApp para el portfolio

## Resumen: ¿cómo de complejo es?

| Opción | Qué se ve desplegado | Dificultad | Coste aprox. | Tiempo |
|---|---|---|---|---|
| **A. Render + MongoDB Atlas** (recomendada para empezar) | La web completa. Kafka no (el catálogo se carga del CSV al arrancar). | ⭐⭐ Baja | 0 € | 30–60 min |
| **B. Un VPS con Docker Compose** | **Todo**: web, Kafka, productor, consumidor, MongoDB y el panel de Kafka. | ⭐⭐⭐ Media | 0–5 €/mes | 2–3 h |
| C. Railway / Fly.io con varios servicios | Todo, como servicios separados. | ⭐⭐⭐ Media | 5–20 €/mes (Kafka consume RAM) | 2 h |

> Los precios y planes gratuitos cambian a menudo. Antes de elegir, comprueba las condiciones
> actuales en la web de cada proveedor.

**Mi recomendación**: empieza con la **opción A** (gratis y en una tarde). En el portfolio pon
el enlace a la demo, el enlace al código y una frase del estilo *"En producción la demo carga
el catálogo directamente; el pipeline con Kafka se puede ver arrancando el `docker compose`
del repositorio"*. Si más adelante quieres enseñar Kafka funcionando, pasa a la opción B.

¿Por qué no se despliega Kafka gratis? Kafka necesita una máquina encendida todo el tiempo con
~1 GB de RAM. Los planes gratuitos de Render, Koyeb, etc. dan 512 MB y "duermen" el servicio.

---

## Antes de nada (cualquier opción)

1. **Revoca el secreto antiguo de Google** (ver [CAMBIOS.md](CAMBIOS.md#1-lo-que-tienes-que-hacer-tú-urgente)).
2. **Sube esta carpeta a un repositorio nuevo de GitHub**, por ejemplo `fitnessapp`:
   ```bash
   cd C:\FitnessApp2026
   git init -b main
   git add .
   git commit -m "FitnessApp 2.0"
   ```
   Crea el repositorio vacío en GitHub y sigue las instrucciones de "push an existing repository".
   Comprueba que **`.env` NO aparece** en GitHub (está en `.gitignore`).
3. Al subirlo, GitHub Actions ejecutará los tests automáticamente (pestaña *Actions*).

---

## Opción A — Render + MongoDB Atlas (gratis)

```mermaid
flowchart LR
    V((Visitante)) -- https --> R[Render<br/>contenedor web]
    R --> A[(MongoDB Atlas<br/>M0 gratis)]
    R --> N[Nominatim]
```

### 1. Base de datos en MongoDB Atlas

1. Crea una cuenta en <https://www.mongodb.com/cloud/atlas> y un clúster **M0 (Free)**.
   Elige una región en Europa (p. ej. Frankfurt o Irlanda).
2. *Database Access* → *Add New Database User*: usuario `fitnessapp`, contraseña larga **solo
   con letras y números**, rol *Read and write to any database* (o `readWrite` sobre `fitnessapp`).
3. *Network Access* → *Add IP Address* → `0.0.0.0/0`. Render no tiene una IP fija en el plan
   gratuito, así que hay que permitir todas; la protección es el usuario y la contraseña.
4. *Connect* → *Drivers* → copia la cadena y **añade el nombre de la base de datos** tras el `/`:
   ```
   mongodb+srv://fitnessapp:TU_PASSWORD@cluster0.xxxxx.mongodb.net/fitnessapp?retryWrites=true&w=majority
   ```

### 2. La web en Render

1. Crea una cuenta en <https://render.com> e inicia sesión con GitHub.
2. *New* → *Blueprint* → elige tu repositorio. Render lee `render.yaml` y crea el servicio.
3. Te pedirá las variables marcadas como secretas:
   - `MONGO_URI`: la cadena de Atlas del paso anterior.
   - `NOMINATIM_USER_AGENT`: `FitnessApp/2.0 (tu-email@ejemplo.com)`.
   - `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`: déjalos vacíos de momento.
   - `SECRET_KEY` la genera Render sola.
4. Espera al primer despliegue (5–10 min). Al arrancar, como `SEED_ON_START=true` y la base
   de datos está vacía, la web carga los 2.225 alimentos del CSV.
5. Abre `https://fitnessapp-xxxx.onrender.com` → *Log in* → *Try it as a guest*.

**A tener en cuenta del plan gratuito de Render**: el servicio se duerme tras unos minutos sin
visitas y la siguiente visita tarda ~30–60 s en despertarlo. Para un portfolio es aceptable;
puedes avisarlo junto al enlace ("la demo puede tardar unos segundos en arrancar").

### 3. (Opcional) Login con Google en producción

1. En Google Cloud Console crea un **cliente OAuth nuevo** (tipo *Aplicación web*).
2. *Orígenes autorizados*: `https://fitnessapp-xxxx.onrender.com`
3. *URI de redirección*: `https://fitnessapp-xxxx.onrender.com/auth/callback`
4. *Pantalla de consentimiento de OAuth*: mientras esté en modo **Testing**, solo pueden entrar
   las cuentas que añadas como *test users*. Para que entre cualquiera hay que pasarla a
   **In production**. Con los permisos que usa la app (`openid email profile`) normalmente
   no hace falta la verificación completa de Google, pero puede pedirte verificar la marca.
5. Pon el ID y el secreto en las variables de Render y redespliega.

Como el modo invitado ya funciona, este paso no es imprescindible para el portfolio.

### 4. Dominio propio (opcional)

En Render: *Settings* → *Custom Domains*. Añade p. ej. `fitness.tudominio.com` y crea el
registro CNAME que te indica. El certificado https es automático. Si usas Google, añade
también el nuevo dominio en el cliente OAuth.

---

## Opción B — VPS con todo el docker-compose

Para enseñar **la arquitectura completa** funcionando.

Proveedores habituales: Oracle Cloud *Always Free* (máquinas ARM gratuitas, aunque a veces no
hay capacidad), Hetzner (desde ~4–5 €/mes), DigitalOcean, OVH… Busca **2 GB de RAM** como
mínimo (Kafka + MongoDB + web).

### Pasos

1. Crea un servidor Ubuntu 24.04 y apunta un dominio (o subdominio) a su IP con un registro A.
2. Instala Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
3. Clona tu repositorio y crea el `.env` (con `SESSION_COOKIE_SECURE`, ver abajo):
   ```bash
   git clone https://github.com/TU_USUARIO/fitnessapp.git && cd fitnessapp
   cp .env.example .env && nano .env
   ```
4. Añade un proxy con https automático. Crea `docker-compose.override.yml`:
   ```yaml
   services:
     web:
       environment:
         SESSION_COOKIE_SECURE: "true"
         PROXY_COUNT: "1"
       ports: !reset []
     caddy:
       image: caddy:2
       restart: unless-stopped
       ports: ["80:80", "443:443"]
       command: caddy reverse-proxy --from fitness.tudominio.com --to web:8000
       volumes: [caddy_data:/data]
       depends_on: [web]
   volumes:
     caddy_data:
   ```
   Caddy obtiene el certificado de Let's Encrypt solo.
5. Arranca:
   ```bash
   docker compose up -d --build
   ```
6. Para enseñar el panel de Kafka sin exponerlo a internet, ábrelo con un túnel SSH desde tu PC:
   ```bash
   ssh -L 8080:localhost:8080 usuario@tu-servidor
   ```
   (antes, en el servidor: `docker compose --profile tools up -d kafka-ui`) y abre <http://localhost:8080>.

Mantenimiento: `git pull && docker compose up -d --build` para actualizar, y activa las
actualizaciones automáticas de seguridad de Ubuntu (`unattended-upgrades`).

---

## Checklist final para el portfolio

- [ ] Secreto antiguo de Google revocado.
- [ ] Repositorio antiguo privado/archivado, o historial limpiado.
- [ ] Repositorio nuevo con el README (la vista previa de GitHub dibuja el diagrama).
- [ ] La pestaña *Actions* de GitHub en verde.
- [ ] Demo desplegada y probada en el móvil.
- [ ] En el portfolio: captura o GIF, enlace a la demo, enlace al código y 3–4 líneas con lo
      que demuestra (Flask, MongoDB, Kafka, Docker, OAuth, tests, CI).
- [ ] Aviso de que la demo puede tardar unos segundos en arrancar (si usas Render gratis).
