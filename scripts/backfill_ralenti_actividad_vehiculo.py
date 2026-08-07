"""Backfill marcha_totals.__by_vehiculo__ from RSV Excels (Actividad rows)."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\Users\ferna\OneDrive\GOS\GOS Hs Ralenti\Horas Ralenti")
DB = Path(r"c:\Users\ferna\OneDrive\GOS\GOS Objetivos\instance\gos.db")


def dur_min(v) -> float:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    if hasattr(v, "hour"):
        return v.hour * 60 + v.minute + getattr(v, "second", 0) / 60
    if isinstance(v, (int, float)):
        return float(v) * 24 * 60
    m = re.match(r"(\d+):(\d+):(\d+)", str(v))
    if m:
        return int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 60
    return 0.0


def parse_actividad_by_vehiculo(path: Path) -> dict[str, dict[str, float]]:
    xl = pd.ExcelFile(path)
    out: dict[str, dict[str, float]] = {}
    for sheet in xl.sheet_names:
        persona = sheet.strip()
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        if df.shape[0] < 9:
            continue
        hdr = [str(x or "").strip().lower() for x in df.iloc[7].tolist()]

        def ci(keys):
            for k in keys:
                for i, h in enumerate(hdr):
                    if k in h:
                        return i
            return -1

        i_veh, i_dur, i_est = ci(["veh"]), ci(["dur"]), ci(["estado"])
        if i_veh < 0 or i_dur < 0 or i_est < 0:
            continue
        by_v: dict[str, float] = defaultdict(float)
        for _, row in df.iloc[8:].iterrows():
            est = str(row.iloc[i_est] or "").lower()
            if "activ" not in est:
                continue
            veh = str(row.iloc[i_veh] or "").strip()
            dm = dur_min(row.iloc[i_dur])
            if veh and dm > 0:
                by_v[veh] += dm
        if by_v:
            out[persona] = {k: round(v, 2) for k, v in by_v.items()}
    return out


def main() -> None:
    import sqlite3

    if not ROOT.is_dir():
        raise SystemExit(f"No existe carpeta: {ROOT}")
    if not DB.is_file():
        raise SystemExit(f"No existe DB: {DB}")

    files_on_disk = {p.name: p for p in ROOT.glob("RSV_*.xls*")}
    print(f"Excels en carpeta: {len(files_on_disk)}")

    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    rows = cur.execute("SELECT id, name, marcha_totals FROM ralenti_files").fetchall()
    updated = 0
    missing = []
    for fid, name, mt_raw in rows:
        path = files_on_disk.get(name)
        if not path:
            # try case-insensitive
            path = next((p for n, p in files_on_disk.items() if n.lower() == name.lower()), None)
        if not path:
            missing.append(name)
            continue
        print(f"Parseando {name} ...")
        by_v = parse_actividad_by_vehiculo(path)
        mt = json.loads(mt_raw or "{}")
        if by_v:
            mt["__by_vehiculo__"] = by_v
        elif "__by_vehiculo__" in mt:
            del mt["__by_vehiculo__"]
        cur.execute(
            "UPDATE ralenti_files SET marcha_totals=? WHERE id=?",
            (json.dumps(mt, ensure_ascii=False), fid),
        )
        n_personas = len(by_v)
        n_vehs = sum(len(v) for v in by_v.values())
        print(f"  OK: {n_personas} choferes, {n_vehs} pares chofer-unidad")
        updated += 1
    con.commit()
    con.close()
    print(f"\nActualizados: {updated}/{len(rows)}")
    if missing:
        print(f"Sin Excel en carpeta ({len(missing)}):")
        for n in missing[:20]:
            print(" ", n)
        if len(missing) > 20:
            print(f"  ... y {len(missing)-20} más")


if __name__ == "__main__":
    main()
