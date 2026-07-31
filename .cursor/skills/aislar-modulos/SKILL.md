---
name: aislar-modulos
description: >-
  Avisa y pide confirmación antes de modificar archivos de un módulo distinto
  al que se está trabajando en GOS Objetivos. Usar al editar código, templates,
  scripts o datos de capacitacion, dashboard, hwo/Análisis, mantenimiento/VTV,
  objetivos, om, ralenti o vacaciones; también si un cambio toca código
  compartido o el importador de base de datos.
---

# Aislar módulos GOS

## Objetivo

Si el usuario trabaja en **un módulo** y un cambio tocaría **otro módulo** (o código compartido riesgoso), **parar, avisar y esperar decisión**. No modificar el otro módulo sin confirmación explícita.

## Mapa de módulos (ownership)

| Módulo (cómo lo nombra el usuario) | Rutas típicas |
|------------------------------------|---------------|
| Capacitación | `gos/modulos/capacitacion/`, templates `capacitacion/` |
| Dashboard | `gos/modulos/dashboard/` |
| Análisis / HWO | `gos/modulos/hwo/`, `instance/hwo/` |
| Mantenimiento / VTV | `gos/modulos/mantenimiento/` |
| Objetivos / FODA / KPIs | `gos/modulos/objetivos/` |
| O&M | `gos/modulos/om/` |
| Ralentí | `gos/modulos/ralenti/` |
| Vacaciones | `gos/modulos/vacaciones/` |

**Compartido / riesgo alto** (avisar siempre si la tarea es de un módulo concreto):

- `gos/extensions.py`, `gos/env.py`, `gos/__init__.py`, `run.py`, `wsgi.py`
- Shell/nav global (`templates` base, menú lateral compartido)
- `gos/modulos/objetivos/services/import_service.py` y scripts de backup/import a Render
- Cualquier cambio que trunque/reemplace tablas de **otros** módulos

## Procedimiento

1. **Identificar el módulo foco** del pedido del usuario (explícito o por archivos que abrió).
2. **Antes de editar**, listar rutas que vas a tocar y clasificarlas: mismo módulo / otro módulo / compartido.
3. Si hay **otro módulo** o **compartido riesgoso**:
   - **No editar todavía** esas rutas.
   - Avisar en una lista corta: archivo → módulo dueño → por qué haría falta.
   - Preguntar: ¿permitís modificarlo, lo evitamos, o lo dejamos para otra rama/tarea?
4. Solo continuar en esas rutas si el usuario dice que sí (o elige una alternativa).
5. Si el cambio es inevitable (bug compartido, nav, importador), explicarlo y pedir OK igual.

## Qué NO hacer

- No “de paso” arreglar Capacitación mientras se pide VTV.
- No asumir que tocar `import_service` / subir `gos.db` es inocuo: puede afectar otros módulos.
- No silenciar el aviso porque el cambio sea “chico”.

## Ejemplo de aviso

> Estamos en **Mantenimiento/VTV**. Para esto también tocaría:
> - `gos/modulos/vacaciones/...` (Vacaciones) — razón breve
> - `import_service.py` (compartido / todos los módulos) — razón breve  
> ¿Los modifico, los evito, o lo hacemos aparte?
