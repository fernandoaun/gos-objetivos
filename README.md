# Planeamiento Estratégico — GOS Objetivos

Aplicación de gestión de **Objetivos Estratégicos**, **Metas** y **KPI** basada en análisis **FODA**, con asistencia de IA, seguimiento mensual y dashboard ejecutivo. Proyecto **autónomo** (no integrado con QDV ni otros sistemas externos por defecto).

## Estado actual

**Etapa 1 implementada** — App Flask runnable con login, dashboard, menú de 9 secciones (placeholders) y catálogos en Configuración.

### Inicio rápido (recomendado)

1. **Doble clic en `ABRIR GOS Objetivos.bat`** → abre el navegador sin ventanas negras (servidor en segundo plano).
2. (Opcional, una vez) **Doble clic en `CREAR ICONO EN ESCRITORIO.vbs`** → icono en el Escritorio con el logo GOS.

Login: `admin@demo.local` / `admin123` — Ver también `COMO ABRIR.txt`

### Por consola

```powershell
cd "C:\Users\ferna\OneDrive\GOS\GOS Objetivos"
python -m pip install -r requirements.txt
python scripts\init_db.py
python scripts\seed_demo.py
python run.py
```

En PowerShell antiguo **no uses `&&`**; usá una línea por comando o `;` entre comandos.

Más ayuda: ver `INICIO.txt`

## Documentación

Toda la especificación de diseño está en [`docs/README.md`](docs/README.md):

| Documento | Descripción |
|-----------|-------------|
| [01-vision-y-alcance](docs/01-vision-y-alcance.md) | Alcance, actores, vínculos externos |
| [02-arquitectura-tecnica](docs/02-arquitectura-tecnica.md) | Stack Flask, API, IA, seguridad |
| [03-estructura-carpetas](docs/03-estructura-carpetas.md) | Árbol del proyecto |
| [04-modelo-datos](docs/04-modelo-datos.md) | ERD y tablas normalizadas |
| [05-wireframes](docs/05-wireframes.md) | Pantallas y UX |
| [06-flujo-navegacion](docs/06-flujo-navegacion.md) | Rutas y flujos de usuario |
| [07-plan-desarrollo](docs/07-plan-desarrollo.md) | 9 etapas de implementación |

## Stack (planificado)

- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js, Plotly
- **Backend:** Python, Flask, SQLAlchemy
- **Base de datos:** SQLite (dev) → PostgreSQL (prod)
- **IA:** OpenAI API

## Licencia / uso

Proyecto GOS Objetivos.
