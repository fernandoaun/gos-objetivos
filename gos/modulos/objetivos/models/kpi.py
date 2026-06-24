from gos.extensions import db
from gos.models.base import TimestampMixin

KPI_AGREGACION_TIPOS = ("suma", "cumplimiento", "promedio", "ultimo")

# Etiquetas cortas para la columna Tipo de la tabla
KPI_TIPO_MEDICION_OPCIONES = (
    ("suma", "Acumulable"),
    ("cumplimiento", "% Cumpl."),
    ("promedio", "% Prom."),
    ("ultimo", "V. mensual"),
)

KPI_TIPO_MEDICION_TITULOS = {
    "suma": "Acumulable — suma mes a mes hasta la meta",
    "cumplimiento": "% Cumplimiento — la meta es un %; si el último mes lo alcanza o supera, está en meta",
    "promedio": "% Promedio — promedio de los % mensuales comparado con la meta",
    "ultimo": "Valor mensual — meta puntual; se mira el cumplimiento del último mes cargado",
}

KPI_TIPO_MEDICION_LABELS = dict(KPI_TIPO_MEDICION_OPCIONES)

KPI_AGREGADO_LABELS = {
    "suma": "Acum.",
    "cumplimiento": "Últ. %",
    "promedio": "Prom. %",
    "ultimo": "Último",
}

MESES_KPI = list(range(1, 13))
MESES_KPI_LABELS = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)


class KpiIndicador(db.Model, TimestampMixin):
    __tablename__ = "kpi_indicadores"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_kpi_indicador_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    numero = db.Column(db.Integer, nullable=True)
    codigo = db.Column(db.String(30), nullable=False)
    indicador = db.Column(db.String(250), nullable=False)
    objetivo_codigo = db.Column(db.String(20), nullable=True)
    responsable = db.Column(db.String(250), nullable=True)
    medio = db.Column(db.String(150), nullable=True)
    resultado_2025 = db.Column(db.String(80), nullable=True)
    meta_2026 = db.Column(db.String(80), nullable=True)
    meta_2026_num = db.Column(db.Float, nullable=True)
    valores_mes = db.Column(db.JSON, default=dict, nullable=False)
    tipo_agregacion = db.Column(db.String(20), default="promedio", nullable=False)
    observacion = db.Column(db.Text, nullable=True)
    grupo = db.Column(db.String(80), nullable=True)
    orden = db.Column(db.Integer, default=0, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
