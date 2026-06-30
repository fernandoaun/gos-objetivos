from gos.modulos.capacitacion.models.alerta import AlertaCapacitacion
from gos.modulos.capacitacion.models.catalogo import CertificacionTipo, Curso, Puesto, TIPOS_CAPACITACION
from gos.modulos.capacitacion.models.config import CapacitacionConfig
from gos.modulos.capacitacion.models.instructor import Instructor
from gos.modulos.capacitacion.models.participante import Participante
from gos.modulos.capacitacion.models.programa import (
    EncuentroCapacitacion,
    EncuentroTema,
    InscripcionPrograma,
    ProgramaCapacitacion,
)
from gos.modulos.capacitacion.models.registro import (
    AsistenciaEncuentro,
    CertificacionEmpleado,
    PlanCapacitacion,
    RegistroCapacitacion,
    RequisitoFormacion,
)
from gos.modulos.capacitacion.models.taxonomia_item import TaxonomiaItem

__all__ = [
    "Puesto",
    "Curso",
    "TIPOS_CAPACITACION",
    "CertificacionTipo",
    "CapacitacionConfig",
    "Instructor",
    "AlertaCapacitacion",
    "Participante",
    "ProgramaCapacitacion",
    "EncuentroCapacitacion",
    "EncuentroTema",
    "InscripcionPrograma",
    "RequisitoFormacion",
    "AsistenciaEncuentro",
    "RegistroCapacitacion",
    "CertificacionEmpleado",
    "PlanCapacitacion",
    "TaxonomiaItem",
]
