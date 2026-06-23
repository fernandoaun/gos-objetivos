from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required


def requiere_login(fn):
    return login_required(fn)


def requiere_rol(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.rol not in roles and current_user.rol != "admin":
                flash("No tenés permiso para esta acción.", "danger")
                return redirect(url_for("dashboard.index"))
            return fn(*args, **kwargs)

        return wrapped

    return decorator
