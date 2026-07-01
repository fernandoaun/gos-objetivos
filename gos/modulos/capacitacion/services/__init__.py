"""Servicios de análisis y seguimiento de capacitaciones."""

from gos.modulos.capacitacion.services.alerta_service import (
    generar_alertas,
    listar_alertas,
    marcar_alerta_leida,
)
from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.catalogo_service import (
    actualizar_curso,
    actualizar_participante,
    actualizar_puesto,
    actualizar_sector,
    baja_curso,
    baja_participante,
    obtener_participante,
    crear_curso,
    crear_participante,
    crear_puesto,
    crear_sector,
    listar_cursos,
    listar_puestos,
    listar_sectores,
    obtener_taxonomia_cursos,
)
from gos.modulos.capacitacion.services.config_service import guardar_config, obtener_config
from gos.modulos.capacitacion.services.dashboard_service import (
    encuentros_cronograma,
    resumen_dashboard,
)
from gos.modulos.capacitacion.services.evidencia_service import (
    descargar_certificado_registro,
    descargar_documento_certificacion,
    descargar_foto_participante,
    eliminar_certificado_registro,
    eliminar_foto_participante,
    subir_certificado_registro,
    subir_documento_certificacion,
    subir_foto_participante,
)
from gos.modulos.capacitacion.services.matriz_service import matriz_capacitaciones
from gos.modulos.capacitacion.services.programa_service import (
    actualizar_encuentro,
    crear_encuentro,
    crear_programa,
    detalle_encuentro,
    inscribir_participantes,
    listar_programas,
    participantes_encuentro,
    registrar_asistencias,
)
from gos.modulos.capacitacion.services.requisito_service import (
    crear_requisito,
    eliminar_requisito,
    listar_requisitos,
)
from gos.modulos.capacitacion.services.import_service import (
    importar_cursos_excel,
    importar_participantes_excel,
)
from gos.modulos.capacitacion.services.reporte_service import reporte_iso, resumen_general_auditoria
from gos.modulos.capacitacion.services.sync_service import sincronizar_legajos_vacaciones
from gos.modulos.capacitacion.services.busqueda_service import busqueda_global
from gos.modulos.capacitacion.services.notificacion_service import enviar_notificaciones_alertas

__all__ = [
    "analitico_participante",
    "matriz_capacitaciones",
    "resumen_dashboard",
    "encuentros_cronograma",
    "generar_alertas",
    "listar_alertas",
    "marcar_alerta_leida",
    "obtener_config",
    "guardar_config",
    "listar_cursos",
    "obtener_taxonomia_cursos",
    "listar_puestos",
    "listar_sectores",
    "crear_curso",
    "actualizar_curso",
    "baja_curso",
    "crear_sector",
    "crear_puesto",
    "crear_participante",
    "actualizar_sector",
    "actualizar_puesto",
    "actualizar_participante",
    "baja_participante",
    "obtener_participante",
    "listar_requisitos",
    "crear_requisito",
    "eliminar_requisito",
    "importar_participantes_excel",
    "importar_cursos_excel",
    "listar_programas",
    "crear_programa",
    "crear_encuentro",
    "actualizar_encuentro",
    "inscribir_participantes",
    "registrar_asistencias",
    "detalle_encuentro",
    "participantes_encuentro",
    "subir_certificado_registro",
    "descargar_certificado_registro",
    "eliminar_certificado_registro",
    "subir_documento_certificacion",
    "descargar_documento_certificacion",
    "subir_foto_participante",
    "descargar_foto_participante",
    "eliminar_foto_participante",
    "reporte_iso",
    "resumen_general_auditoria",
    "sincronizar_legajos_vacaciones",
    "busqueda_global",
    "enviar_notificaciones_alertas",
]
