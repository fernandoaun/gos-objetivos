"""Constantes SGC para GOS."""

SGI_REGISTRO_MODULOS: dict[str, dict[str, str]] = {
    "mantenimiento": {
        "label": "Mantenimiento",
        "blank_endpoint": "mantenimiento_main.index",
        "filled_endpoint": "mantenimiento_main.index",
    },
    "capacitacion": {
        "label": "Capacitación",
        "blank_endpoint": "capacitacion_main.index",
        "filled_endpoint": "capacitacion_main.index",
    },
    "om": {
        "label": "O&M",
        "blank_endpoint": "om_main.index",
        "filled_endpoint": "om_main.index",
    },
}
