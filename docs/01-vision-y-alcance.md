# 1. Visión y alcance

## 1.1 Propósito del módulo

**Planeamiento Estratégico** permite a una organización:

- Registrar y mantener un análisis **FODA** estructurado.
- Obtener **análisis cruzado** (FO, DO, FA, DA) e informes con **IA**.
- Definir **Objetivos Estratégicos**, **Metas** y **KPI** (sugeridos por IA o manuales).
- Realizar **seguimiento mensual** con cálculo automático de avances, desvíos y tendencias.
- Visualizar cumplimiento en un **dashboard ejecutivo** con semáforos.
- Activar **planes de acción** cuando un KPI está fuera de objetivo.
- Recibir **predicciones y alertas** basadas en histórico.
- **Vincular** con sistemas externos: **fuera de v1** (backlog).

## 1.2 Objetivo general (funcional)

| Capacidad | Descripción |
|-----------|-------------|
| FODA | CRUD, búsqueda, filtros, export Excel/PDF |
| IA FODA | Cruces FO/DO/FA/DA + informe (situación, riesgos, oportunidades, recomendaciones) |
| Objetivos | Sugerencia IA, aceptar/modificar/eliminar/crear manual |
| Metas | Múltiples por objetivo, con valor objetivo y unidad |
| KPI | Múltiples por meta, fórmula, frecuencia, valor objetivo |
| Seguimiento | Registros periódicos, evidencias, métricas automáticas |
| Planes de acción | Auto-generación al incumplir KPI |
| Dashboard | Indicadores, gráficos Plotly/Chart.js, semáforo |
| Predicción IA | Probabilidad cumplimiento, KPI críticos, recomendaciones |
| Vínculos externos | Backlog (post v1) |

## 1.3 Actores

| Actor | Uso principal |
|-------|----------------|
| Dirección / Gerencia | Dashboard, reportes, aprobación objetivos |
| Responsable de área | FODA, objetivos, metas, seguimiento de su área |
| Analista / Calidad | Configuración, integración SGI, exportaciones |
| Administrador sistema | Configuración empresa, API keys IA, permisos |

## 1.4 Alcance IN / OUT

### Dentro del alcance (v1)

- Aplicación web autocontenida con menú de 9 secciones.
- SQLite en desarrollo; capa de acceso a datos compatible con PostgreSQL.
- OpenAI API para análisis FODA, sugerencias y predicciones.
- Tema claro/oscuro, layout responsive con sidebar.
- Multi-empresa preparado a nivel de modelo (`empresa_id` en tablas maestras).

### Fuera del alcance inicial (backlog)

- Workflow de aprobación multi-nivel con firma digital.
- App móvil nativa.
- ETL automático desde ERP (solo carga manual de valores KPI en v1).
- Motor de reglas propio sin IA (opcional en fases posteriores).

## 1.5 Vínculos externos

**No incluido en v1.** La tabla `sgi_vinculos` y el adaptador se diseñaron para una fase posterior si hace falta enlazar con ERP u otros sistemas.

## 1.6 Principios de diseño UX

Inspiración visual: **Power BI**, **Monday**, **ClickUp**, **Notion**.

- Navegación lateral fija con iconografía clara.
- Tarjetas (cards) para KPI y objetivos con progreso circular/barra.
- Tablas con filtros persistentes en URL.
- Acciones primarias visibles; IA como asistente lateral (drawer), no bloqueante.
- Estados vacíos con CTA (“Cargar primer FODA”, “Ejecutar análisis IA”).

## 1.7 Métricas de éxito del módulo

- Tiempo desde FODA cargado hasta primer objetivo aceptado &lt; 30 min (con IA).
- Dashboard carga en &lt; 2 s con hasta 50 KPI activos.
- Cálculo de avance/desvío consistente y auditable (fórmulas documentadas).
- Export PDF/Excel sin pérdida de columnas definidas en spec.
