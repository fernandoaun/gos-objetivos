from gos.modulos.capacitacion.models.acreditacion import Acreditacion
from gos.modulos.capacitacion.models.alerta import AlertaCapacitacion
from gos.modulos.capacitacion.models.catalogo import (
    Centro,
    CertificacionTipo,
    Curso,
    EmpresaCapacitadora,
    Puesto,
    TIPOS_CAPACITACION,
)
from gos.modulos.capacitacion.models.config import CapacitacionConfig
from gos.modulos.capacitacion.models.instructor import Instructor
from gos.modulos.capacitacion.models.participante import Participante
from gos.modulos.capacitacion.models.programa import (
    CronogramaPuesto,
    EncuentroCapacitacion,
    EncuentroTema,
    InscripcionPrograma,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
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
    "Acreditacion",
    "Centro",
    "Puesto",
    "Curso",
    "EmpresaCapacitadora",
    "TIPOS_CAPACITACION",
    "CertificacionTipo",
    "CapacitacionConfig",
    "Instructor",
    "AlertaCapacitacion",
    "Participante",
    "ProgramaCapacitacion",
    "ProgramaPlan",
    "PlanCurso",
    "ProgramaPuesto",
    "CronogramaPuesto",
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
