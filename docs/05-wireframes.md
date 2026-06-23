# 5. Wireframes y diseño de pantallas

Leyenda: `[ ]` botón · `{ }` campo · `▓` gráfico · `●` semáforo

Todas las pantallas comparten **layout**: sidebar izquierda (240px) + topbar (logo GOS Objetivos, empresa, usuario, 🌙 tema).

---

## 5.1 Layout maestro

```
┌──────────────────────────────────────────────────────────────────────────┐
│ GOS  │ Planeamiento Estratégico          Empresa XYZ    [Usuario ▼] [🌙] │
├────────────┬─────────────────────────────────────────────────────────────┤
│ ● FODA     │                                                             │
│   Objetivos│                    CONTENIDO PRINCIPAL                      │
│   Metas    │                    (cards, tablas, gráficos)                │
│   KPI      │                                                             │
│   Seguim.  │                                                             │
│   Dashboard│                                                             │
│   Planes   │                                                             │
│   Reportes │                                                             │
│   Config   │                                                             │
└────────────┴─────────────────────────────────────────────────────────────┘
```

**Responsive:** sidebar colapsa a iconos (&lt;992px); menú hamburguesa en móvil.

---

## 5.2 FODA — Listado por cuadrantes

**Ruta:** `/planeamiento/foda/`

```
┌─────────────────────────────────────────────────────────────────┐
│ FODA                                    [+ Nuevo] [Export ▼]    │
│ [Buscar...        ] [Tipo ▼] [Área ▼] [Responsable ▼] [Fecha] │
├─────────────────────────────────────────────────────────────────┤
│ [Fortalezas] [Oportunidades] [Debilidades] [Amenazas]  ← tabs   │
├─────────────────────────────────────────────────────────────────┤
│ Código │ Descripción      │ Área    │ Responsable │ Fecha │ ⋮  │
│ F-001  │ Equipo certificado │ Calidad │ Juan P.     │ 01/03 │ ✎ 🗑│
│ F-002  │ ...                │         │             │       │    │
├─────────────────────────────────────────────────────────────────┤
│ Paginación                              Mostrando 1-20 de 45    │
└─────────────────────────────────────────────────────────────────┘

Barra flotante IA: [✨ Analizar FODA con IA]
```

**Modal crear/editar:** tipo (pre-seleccionado por tab), código auto, descripción textarea, área select, responsable select, fecha.

**Export:** Excel (4 hojas o 1 con columna tipo), PDF matriz 2×2 visual opcional.

---

## 5.3 Análisis IA del FODA

**Ruta:** `/planeamiento/foda/analisis`

```
┌─────────────────────────────────────────────────────────────────┐
│ Análisis estratégico FODA          [Regenerar] [Exportar PDF]   │
├──────────────────────────┬──────────────────────────────────────┤
│ Cruce FO (Fort+Oport)    │  Situación actual                    │
│ • Estrategia 1           │  Lorem resumen ejecutivo...          │
│ • Estrategia 2           ├──────────────────────────────────────┤
├──────────────────────────┤  Riesgos │ Oportunidades             │
│ Cruce DO                 │  (dos columnas cards)                │
├──────────────────────────┤                                      │
│ Cruce FA                 │  Recomendaciones                     │
├──────────────────────────┤  • Acción prioritaria 1              │
│ Cruce DA                 │  • Acción prioritaria 2              │
└──────────────────────────┴──────────────────────────────────────┘

[Generar objetivos sugeridos desde este análisis →]
```

Drawer lateral durante generación: spinner + “Analizando 24 ítems FODA…”.

---

## 5.4 Objetivos estratégicos

**Ruta:** `/planeamiento/objetivos/`

```
┌─────────────────────────────────────────────────────────────────┐
│ Objetivos Estratégicos    [+ Manual]  [Ver sugerencias IA (3)]  │
│ Filtros: Estado │ Categoría │ Responsable │ Rango fechas        │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│ │ OBJ-001      │ │ OBJ-002      │ │ + Nueva card │              │
│ │ Incr. ventas │ │ Reducir costos│              │              │
│ │ ● Activo 78% │ │ ● Riesgo 62% │ │              │              │
│ │ Metas: 3     │ │ Metas: 2     │ │              │              │
│ └──────────────┘ └──────────────┘ └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

**Detalle objetivo** (`/objetivos/{id}`):

- Cabecera: código, nombre, estado badge, fechas, responsable.
- Tabs: Resumen | Metas | KPI (agregado) | Vínculos SGI | Historial IA.
- Acciones: Editar, Cambiar estado, Eliminar (confirm).

**Panel sugerencias IA:**

| Sugerencia | Categoría | [Aceptar] [Editar] [Rechazar] |
|------------|-----------|-------------------------------|

---

## 5.5 Metas

**Ruta:** `/planeamiento/metas/` o anidado en objetivo

```
Objetivo: [Incrementar ventas ▼]

┌─────────────────────────────────────────────────────────────────┐
│ Metas del objetivo                           [+ Agregar meta]   │
├─────────────────────────────────────────────────────────────────┤
│ MET-001 │ Aumentar ventas 15% │ 15 │ % │ 01/01-31/12 │ Juan │ ⋮  │
│ MET-002 │ 10 clientes nuevos  │ 10 │ # │ ...           │      │   │
└─────────────────────────────────────────────────────────────────┘

[✨ Sugerir metas con IA]
```

---

## 5.6 KPI

**Ruta:** `/planeamiento/kpis/`

Tabla con árbol: Meta → KPIs hijos expandibles.

```
│ KPI-001 │ Ventas mensuales │ Ventas act/Ventas obj │ % │ Mensual │ 100 │ │
```

Formulario: fórmula con ayuda (plantillas), preview cálculo con último seguimiento.

---

## 5.7 Seguimiento mensual

**Ruta:** `/planeamiento/seguimiento/`

```
┌─────────────────────────────────────────────────────────────────┐
│ Seguimiento                    Período: [Marzo 2026 ▼]            │
│ KPI: [Todos ▼]  Responsable: [▼]                                 │
├─────────────────────────────────────────────────────────────────┤
│ KPI          │ Objetivo │ Meta │ Real │ Avance │ Desvío │ Tend │ +│
│ Ventas mens. │ Incr...  │ 15%  │ 12%  │ 80% 🟡 │ -3%  │ ↓    │📝│
├─────────────────────────────────────────────────────────────────┤
│ [Cargar seguimiento masivo Excel]                                │
└─────────────────────────────────────────────────────────────────┘
```

**Modal carga:**

- Fecha, KPI (select), valor real, observaciones, [Adjuntar evidencia].

Al guardar: muestra avance calculado en vivo.

---

## 5.8 Planes de acción

**Ruta:** `/planeamiento/planes-accion/`

Kanban opcional (fase 2) — v1 tabla + filtros por estado.

```
│ Auto │ Reducir gastos logísticos │ KPI costos │ Ana │ 15/04 │ Pendiente │
```

Badge “Generado automáticamente” si `auto_generado=true`.

---

## 5.9 Dashboard ejecutivo

**Ruta:** `/planeamiento/dashboard/` (home del módulo)

```
┌────────┬────────┬────────┬────────┬────────┐
│ Obj.   │ Metas  │ KPI    │ Cumpl. │ Alertas│
│ activos│ activas│ activos│ global │   5    │
│   12   │   28   │   45   │  82%🟡 │        │
└────────┴────────┴────────┴────────┴────────┘

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ Cumplimiento por objetivo   │ │ Por sector (barras Plotly)  │
│ ▓▓▓▓▓▓▓▓░░  OBJ-001 92% 🟢  │ │                             │
│ ▓▓▓▓▓░░░░░  OBJ-002 68% 🔴  │ │                             │
└─────────────────────────────┘ └─────────────────────────────┘

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ Evolución mensual (línea)   │ │ Tendencia anual             │
└─────────────────────────────┘ └─────────────────────────────┘

┌─ Predicción IA ─────────────────────────────────────────────┐
│ "Reducir Costos: 62% probabilidad cumplimiento..."          │
│ [Ver detalle] [Actualizar predicción]                       │
└─────────────────────────────────────────────────────────────┘
```

Semáforo global grande (donut Chart.js).

---

## 5.10 Reportes

**Ruta:** `/planeamiento/reportes/`

- Informe FODA + análisis IA (PDF).
- Objetivos y cumplimiento por período.
- Seguimientos con evidencias (listado).
- Planes de acción abiertos.

Wizard: seleccionar rango → formato → [Generar].

---

## 5.11 Configuración

**Ruta:** `/planeamiento/configuracion/`

Tabs:

1. **Umbrales semáforo** (verde/amarillo).
2. **Catálogos:** sectores, áreas, responsables.
3. **IA:** modelo, límites, modo demo.
4. **Planes de acción:** auto-generar sí/no.
5. **Vínculos externos (SGI):** URLs base opcionales para sistemas de terceros.

---

## 5.12 Paleta y componentes visuales

| Token | Claro | Oscuro |
|-------|-------|--------|
| `--pe-bg` | #f4f6f9 | #1a1d23 |
| `--pe-card` | #ffffff | #252930 |
| `--pe-primary` | #2563eb | #3b82f6 |
| `--pe-success` | #16a34a | #22c55e |
| `--pe-warning` | #ca8a04 | #eab308 |
| `--pe-danger` | #dc2626 | #ef4444 |

**Cards:** sombra suave, border-radius 12px, hover lift 2px.  
**Tipografía:** system-ui + Inter (opcional).  
**Iconos:** Bootstrap Icons.

---

## 5.13 Componentes reutilizables

| Componente | Uso |
|------------|-----|
| `card_kpi.html` | Mini KPI con sparkline |
| `semaforo.html` | Badge + tooltip umbrales |
| `modal_ia.html` | Progreso y resultado IA |
| `tabla_filtros.html` | Barra filtros + chips activos |
| `breadcrumb_planeamiento` | Navegación contextual |
