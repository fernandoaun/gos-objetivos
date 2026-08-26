"""Modo de aplicación: plataforma completa, solo Objetivos, o solo Capacitación."""

from __future__ import annotations

from typing import Literal

AppMode = Literal["full", "objetivos", "capacitacion"]

VALID_MODES = frozenset({"full", "objetivos", "capacitacion"})


def normalize_app_mode(raw: str | None) -> AppMode:
    value = (raw or "full").strip().lower()
    if value not in VALID_MODES:
        return "full"
    return value  # type: ignore[return-value]


def capacitacion_enabled(mode: AppMode) -> bool:
    return mode in ("full", "capacitacion")


def objetivos_stack_enabled(mode: AppMode) -> bool:
    """Dashboard + Objetivos + HWO + Vacaciones + Ralentí + Mant + O&M + SGC."""
    return mode in ("full", "objetivos")
