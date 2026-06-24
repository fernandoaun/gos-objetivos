"""Servicios de análisis y seguimiento de capacitaciones."""

from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.dashboard_service import (
    encuentros_calendario,
    resumen_dashboard,
)

__all__ = ["analitico_participante", "resumen_dashboard", "encuentros_calendario"]
