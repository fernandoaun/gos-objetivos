from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required

from gos.models.usuario import usuario_cumple_rol


def requiere_rol(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if not usuario_cumple_rol(current_user, *roles):
                flash("No tenés permiso para esta acción.", "danger")
                return redirect(url_for("main.index"))
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def requiere_admin(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.es_administrador():
            abort(403)
        return fn(*args, **kwargs)

    return wrapped
