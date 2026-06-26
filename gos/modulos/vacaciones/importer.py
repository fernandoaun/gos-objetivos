import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from gos.modulos.vacaciones.models import Registro, Vacacion

COLS_TOTAL = [
    "fecha", "empleado", "sector", "servicio", "centro", "situacion",
    "total_horas", "hs_viaje", "hs50", "hs_noc", "hs_noc50", "hs100",
    "viandas", "v_desayuno", "d_normales", "ausente", "fr_trabajados",
    "feriados", "enfermedad", "traslado", "vacaciones", "licencia",
    "suspension", "accidente", "francos_comp",
]


def _upsert(model, session: Session):
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        return insert(model)
    from sqlalchemy.dialects.sqlite import insert

    return insert(model)


def import_excel(filepath: str, db: Session) -> dict:
    result = {
        "registros": 0,
        "registros_nuevos": 0,
        "registros_actualizados": 0,
        "vacaciones": 0,
        "vacaciones_nuevas": 0,
        "vacaciones_actualizadas": 0,
        "errores": [],
    }

    with pd.ExcelFile(filepath) as xl:
        if "TOTAL" in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name="TOTAL", header=0)
            df.columns = COLS_TOTAL[: len(df.columns)]
            df = df.dropna(subset=["fecha", "empleado"])
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
            df = df.dropna(subset=["fecha"])

            numeric_cols = COLS_TOTAL[6:]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            records = df.to_dict(orient="records")

            if records:
                min_date = df["fecha"].min()
                max_date = df["fecha"].max()
                existing_rows = db.execute(
                    select(Registro.fecha, Registro.empleado).where(
                        Registro.fecha >= min_date,
                        Registro.fecha <= max_date,
                    )
                ).fetchall()
                existing_keys = {(row.fecha, row.empleado) for row in existing_rows}
                keys_en_excel = {(r["fecha"], r["empleado"]) for r in records}
                result["registros_nuevos"] = len(keys_en_excel - existing_keys)
                result["registros_actualizados"] = len(keys_en_excel & existing_keys)

            chunk_size = 500
            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]
                stmt = _upsert(Registro, db).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["fecha", "empleado"],
                    set_={
                        "sector": stmt.excluded.sector,
                        "servicio": stmt.excluded.servicio,
                        "centro": stmt.excluded.centro,
                        "situacion": stmt.excluded.situacion,
                        "total_horas": stmt.excluded.total_horas,
                        "hs_viaje": stmt.excluded.hs_viaje,
                        "hs50": stmt.excluded.hs50,
                        "hs_noc": stmt.excluded.hs_noc,
                        "hs_noc50": stmt.excluded.hs_noc50,
                        "hs100": stmt.excluded.hs100,
                        "viandas": stmt.excluded.viandas,
                        "v_desayuno": stmt.excluded.v_desayuno,
                        "d_normales": stmt.excluded.d_normales,
                        "ausente": stmt.excluded.ausente,
                        "fr_trabajados": stmt.excluded.fr_trabajados,
                        "feriados": stmt.excluded.feriados,
                        "enfermedad": stmt.excluded.enfermedad,
                        "traslado": stmt.excluded.traslado,
                        "vacaciones": stmt.excluded.vacaciones,
                        "licencia": stmt.excluded.licencia,
                        "suspension": stmt.excluded.suspension,
                        "accidente": stmt.excluded.accidente,
                        "francos_comp": stmt.excluded.francos_comp,
                    },
                )
                db.execute(stmt)
            db.commit()
            result["registros"] = len(records)

        if "PLANILLA VACACIONES" in xl.sheet_names:
            df_vac = pd.read_excel(xl, sheet_name="PLANILLA VACACIONES", header=None)
            data_rows = df_vac.iloc[4:].copy()

            def parse_year_block(df, col_offset, anio):
                rows = []
                for _, row in df.iterrows():
                    legajo = row.iloc[0]
                    empleado = row.iloc[1]
                    fecha_ingreso = row.iloc[2]
                    sector = row.iloc[3]
                    disp = row.iloc[col_offset]
                    tomados = row.iloc[col_offset + 1]
                    pendientes = row.iloc[col_offset + 2]

                    if pd.isna(empleado):
                        continue
                    rows.append(
                        {
                            "legajo": int(legajo) if not pd.isna(legajo) else None,
                            "empleado": str(empleado).strip(),
                            "fecha_ingreso": pd.to_datetime(fecha_ingreso, errors="coerce").date()
                            if not pd.isna(fecha_ingreso)
                            else None,
                            "sector": str(sector).strip() if not pd.isna(sector) else None,
                            "anio": anio,
                            "dias_disponibles": int(disp) if not pd.isna(disp) else 0,
                            "dias_tomados": int(tomados) if not pd.isna(tomados) else 0,
                            "dias_pendientes": int(pendientes) if not pd.isna(pendientes) else 0,
                        }
                    )
                return rows

            all_vac = []
            all_vac += parse_year_block(data_rows, 5, 2023)
            all_vac += parse_year_block(data_rows, 9, 2024)
            all_vac += parse_year_block(data_rows, 13, 2025)

            if all_vac:
                anios_en_excel = {r["anio"] for r in all_vac}
                existing_vac = db.execute(
                    select(Vacacion.legajo, Vacacion.anio).where(
                        Vacacion.anio.in_(anios_en_excel)
                    )
                ).fetchall()
                existing_vac_keys = {(row.legajo, row.anio) for row in existing_vac}
                keys_vac_excel = {(r["legajo"], r["anio"]) for r in all_vac}
                result["vacaciones_nuevas"] = len(keys_vac_excel - existing_vac_keys)
                result["vacaciones_actualizadas"] = len(keys_vac_excel & existing_vac_keys)

            for rec in all_vac:
                if not rec["empleado"]:
                    continue
                stmt = _upsert(Vacacion, db).values(rec)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["legajo", "anio"],
                    set_={
                        "empleado": stmt.excluded.empleado,
                        "fecha_ingreso": stmt.excluded.fecha_ingreso,
                        "sector": stmt.excluded.sector,
                        "dias_disponibles": stmt.excluded.dias_disponibles,
                        "dias_tomados": stmt.excluded.dias_tomados,
                        "dias_pendientes": stmt.excluded.dias_pendientes,
                    },
                )
                db.execute(stmt)
            db.commit()
            result["vacaciones"] = len(all_vac)

    return result
