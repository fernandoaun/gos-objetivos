from gos.modulos.capacitacion.models.catalogo import CertificacionTipo, Curso, Puesto
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

__all__ = [
    "Puesto",
    "Curso",
    "CertificacionTipo",
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
]
