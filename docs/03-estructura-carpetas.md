# 3. Estructura de carpetas del proyecto

## 3.1 Árbol completo propuesto

```
GOS Objetivos/                          # Raíz de la aplicación standalone
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml                      # Opcional: tooling (black, ruff)
├── alembic.ini
├── migrations/
│   └── versions/
│       └── 001_initial_planeamiento.py
│
├── app/
│   ├── __init__.py                     # create_app()
│   ├── config.py                       # Dev / Prod / Testing
│   ├── extensions.py                   # db, migrate, limiter, csrf
│   │
│   ├── models/                         # SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py                     # TimestampMixin, EmpresaScoped
│   │   ├── catalogos.py                # Sector, Area, Responsable
│   │   ├── foda.py
│   │   ├── objetivo.py
│   │   ├── meta.py
│   │   ├── kpi.py
│   │   ├── seguimiento.py
│   │   ├── plan_accion.py
│   │   ├── evidencia.py
│   │   ├── foda_ia.py
│   │   ├── sgi_vinculo.py
│   │   └── auditoria.py
│   │
│   ├── schemas/                        # Validación API
│   │   ├── foda.py
│   │   ├── objetivo.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── foda_service.py
│   │   ├── foda_ia_service.py
│   │   ├── objetivo_service.py
│   │   ├── meta_service.py
│   │   ├── kpi_service.py
│   │   ├── kpi_calculator.py
│   │   ├── seguimiento_service.py
│   │   ├── plan_accion_service.py
│   │   ├── dashboard_service.py
│   │   ├── prediccion_ia_service.py
│   │   ├── export_service.py
│   │   └── sgi_adapter.py
│   │
│   ├── repositories/                   # Opcional fase 2+
│   │   └── dashboard_repo.py
│   │
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── main.py                     # Landing / redirect dashboard
│   │   ├── foda.py
│   │   ├── objetivos.py
│   │   ├── metas.py
│   │   ├── kpis.py
│   │   ├── seguimiento.py
│   │   ├── dashboard.py
│   │   ├── planes_accion.py
│   │   ├── reportes.py
│   │   ├── configuracion.py
│   │   └── api/                        # API REST v1
│   │       ├── __init__.py
│   │       ├── foda.py
│   │       ├── objetivos.py
│   │       ├── dashboard.py
│   │       └── ia.py
│   │
│   ├── prompts/
│   │   ├── foda_analisis.yaml
│   │   ├── objetivos_sugeridos.yaml
│   │   ├── metas_kpi.yaml
│   │   └── prediccion.yaml
│   │
│   ├── utils/
│   │   ├── codigos.py                  # Generador FODA-001, OBJ-001
│   │   ├── formula_parser.py
│   │   ├── semaforo.py
│   │   └── dates.py
│   │
│   └── templates/
│       └── planeamiento/
│           ├── base.html               # Layout sidebar + tema
│           ├── components/
│           │   ├── sidebar.html
│           │   ├── card_kpi.html
│           │   ├── semaforo.html
│           │   ├── modal_ia.html
│           │   └── tabla_filtros.html
│           ├── foda/
│           │   ├── list.html
│           │   ├── form.html
│           │   └── analisis_ia.html
│           ├── objetivos/
│           ├── metas/
│           ├── kpis/
│           ├── seguimiento/
│           ├── dashboard/
│           ├── planes_accion/
│           ├── reportes/
│           └── configuracion/
│
├── static/
│   └── planeamiento/
│       ├── css/
│       │   ├── theme.css               # Claro / oscuro
│       │   ├── layout.css
│       │   └── dashboard.css
│       ├── js/
│       │   ├── app.js
│       │   ├── theme-toggle.js
│       │   ├── foda.js
│       │   ├── objetivos.js
│       │   ├── seguimiento.js
│       │   ├── dashboard-charts.js
│       │   └── api-client.js
│       └── img/
│           └── icons/
│
├── storage/                            # Gitignored
│   └── evidencias/{empresa_id}/{year}/
│
├── tests/
│   ├── conftest.py
│   ├── test_kpi_calculator.py
│   ├── test_foda_api.py
│   └── test_dashboard.py
│
├── scripts/
│   ├── seed_demo.py
│   └── init_db.py
│
└── docs/                               # Esta documentación
    ├── README.md
    └── ...
```

## 3.2 Convenciones de nombres

| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| Blueprint | `bp_<seccion>` | `bp_foda` |
| Modelo | PascalCase singular | `FodaItem` |
| Tabla SQL | snake_case plural | `foda_items` |
| Ruta HTML | kebab-case español | `/planeamiento/objetivos-estrategicos` |
| API | snake_case inglés opcional | `/api/v1/planes_accion` |
| JS módulo | un archivo por pantalla principal | `foda.js` |

## 3.3 Despliegue

Este repositorio **es** la aplicación completa. No se embebe en otros productos salvo que más adelante se decida exponer solo una API.

- Desarrollo: `flask run` desde la raíz.
- Producción: Gunicorn + Nginx (ver `docs/deploy.md` en etapa 9).

## 3.4 Archivos de configuración clave

### `.env.example`

```
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///instance/planeamiento.db
# DATABASE_URL=postgresql://user:pass@localhost/gos_objetivos
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
PLANEAMIENTO_EVIDENCIAS_PATH=storage/evidencias
IA_RATE_LIMIT_PER_HOUR=20
```

### `requirements.txt` (núcleo)

```
flask>=3.0
flask-sqlalchemy>=3.1
flask-migrate
flask-wtf
marshmallow
openai
plotly
openpyxl
weasyprint
python-dotenv
psycopg2-binary
```

## 3.5 Plantilla base HTML (contrato)

- `base.html` incluye: sidebar 9 ítems, topbar (empresa, usuario, toggle tema), bloque `{% block content %}`, scripts al final.
- Todos los templates extienden `planeamiento/base.html`.
- IDs data-* para hooks JS: `data-module="foda"`, `data-entity-id="{{ id }}"`.
