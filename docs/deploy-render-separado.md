# Deploy separado en Render (Cap + Objetivos)

Dos servicios web + dos Postgres. El código es el mismo repo; el modo lo marca `GOS_APP_MODE`.

| Servicio | Modo | WSGI | Base |
|----------|------|------|------|
| `gos-objetivos` | `objetivos` | `wsgi:app` | `gos-objetivos-db` |
| `gos-capacitacion` | `capacitacion` | `wsgi_capacitacion:app` | `gos-capacitacion-db` |

Definido en `render.yaml`.

## Pasos

### 1. Commit + push del código (con la separación)

Push a GitHub. En Render, si el Blueprint ya existe, sincronizá el `render.yaml` (o creá el servicio Cap a mano).

### 2. Crear / actualizar servicios

**Opción A — Blueprint**  
Render → Blueprints → sync desde `render.yaml` (crea Cap + su DB).

**Opción B — Manual**

1. Nueva PostgreSQL: `gos-capacitacion-db`
2. Nuevo Web Service `gos-capacitacion`:
   - Build: `pip install -r requirements.txt`
   - Start: `python scripts/render_start.py && gunicorn --bind 0.0.0.0:$PORT --timeout 120 wsgi_capacitacion:app`
   - Env: `FLASK_ENV=production`, `GOS_APP_MODE=capacitacion`, `DATABASE_URL` (de la DB Cap), `SECRET_KEY`, `GOS_ADMIN_PASSWORD`, `GOS_IMPORT_SECRET`, `GOS_AUTO_LOGIN=false`
3. En **gos-objetivos** (existente):
   - `GOS_APP_MODE=objetivos`
   - `GOS_CAPACITACION_URL=https://gos-capacitacion.onrender.com/gos/capacitacion` (ajustá el host real)
   - Redeploy

### 3. Subir datos

**Objetivos** (sin Cap):

```bat
set GOS_LOCAL_DB_PATH=instance\objetivos\gos.db
SUBIR BACKUP A RENDER.bat
```

(Usá el `GOS_IMPORT_SECRET` del servicio **gos-objetivos**.)

**Capacitación**:

```bat
SUBIR CAP A RENDER.bat
```

Pedirá `RENDER_CAP_DATABASE_URL` (URL **externa** de `gos-capacitacion-db` en el dashboard).

### 4. Verificar

- Objetivos: `https://gos-objetivos.onrender.com` → menú Cap abre el otro host
- Cap: `https://gos-capacitacion.onrender.com` → entra a Capacitación

Login: mismos usuarios clonados en cada base (tras el upload). Las contraseñas son las de cada DB; el admin bootstrap puede diferir si no subiste `usuarios`.

## Notas

- **Plan free**: dos web + dos DB puede exigir upgrade; Render a veces limita DB free.
- **Archivos Cap** (`storage/capacitacion/`): el disco de Render es efímero; evidencias hay que resubir o montar disco persistente (pago).
- **Secretos distintos** por servicio (no compartas `SECRET_KEY` / `GOS_IMPORT_SECRET` entre Cap y Objetivos).
- La Cap vieja que quedó en el Postgres histórico de Objetivos puede quedarse huérfana; no afecta al modo `objetivos`. Si querés limpiarla, pedí un script de drop `cap_*` en esa DB.
