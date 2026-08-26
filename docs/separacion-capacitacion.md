# Separación Capacitación / Objetivos (Option B)

Dos programas con **bases distintas** y **perfiles clonados**.

## Una sola vez

1. Ejecutá `SEPARAR CAPACITACION.bat` (o `python scripts/separar_bases_capacitacion.py`).
2. Se crea backup en `instance/backups/gos-antes-separacion-*.db`.
3. Quedan:
   - `instance/capacitacion/gos_cap.db` — `cap_*` + empresas/usuarios/perfiles/sectores/areas/responsables
   - `instance/objetivos/gos.db` — resto de módulos, sin `cap_*`; perfiles sin código `capacitacion`
4. La `instance/gos.db` original **no se borra**.

## Uso diario

| Programa | Cómo abrir | Puerto | Base |
|----------|------------|--------|------|
| Capacitación | `ABRIR CAPACITACION.bat` | 5002 | `instance/capacitacion/gos_cap.db` |
| Objetivos (+ resto) | `ABRIR GOS Objetivos.bat` | 5001 | `instance/objetivos/gos.db` si existe |

En Objetivos, el menú puede mostrar **Capacitación** como enlace externo (`GOS_CAPACITACION_URL`, default `http://127.0.0.1:5002/gos/capacitacion`).

## Variables

- `GOS_APP_MODE=capacitacion|objetivos|full`
- `GOS_DATABASE_PATH` — fuerza el SQLite (gana sobre `DATABASE_URL`)
- `GOS_CAPACITACION_URL` — enlace al otro programa

## Efectos colaterales

- O&M ya no tiene FK a `cap_participantes`; los vínculos `participante_id` se limpian en la base Objetivos.
- Sync Cap ↔ Vacaciones deja de compartir DB (hay que reimportar personas o usar API a futuro).
- Subir backup a Render: cada programa tendrá su propia DB/servicio cuando despliegues Cap por separado (`wsgi_capacitacion:app`).

## Deploy en Render (dos programas)

Ver [deploy-render-separado.md](deploy-render-separado.md): servicios `gos-objetivos` + `gos-capacitacion`, dos Postgres, `SUBIR CAP A RENDER.bat`.
