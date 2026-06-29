def test_perfiles_requiere_admin(client):
    r = client.get("/perfiles/", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_perfiles_crear_y_asignar(auth_client, app):
    r = auth_client.post(
        "/perfiles/",
        data={
            "nombre": "Solo Objetivos",
            "modulos": ["objetivos"],
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"creado correctamente" in r.data

    with app.app_context():
        from gos.models import Perfil

        perfil = Perfil.query.filter_by(nombre="Solo Objetivos").first()
        assert perfil is not None
        assert perfil.modulos == ["objetivos"]

    r = auth_client.post(
        "/usuarios/",
        data={
            "email": "perfil@test.com",
            "nombre": "Con Perfil",
            "password": "clave123",
            "rol": "angel",
            "perfil_id": str(perfil.id),
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"creado correctamente" in r.data


def test_usuario_con_perfil_solo_ve_modulos_asignados(client, app):
    with app.app_context():
        from gos.extensions import db
        from gos.models import Empresa, Perfil, Usuario
        from gos.services.modulo_service import codigos_modulos_permitidos

        emp = Empresa.query.first()
        perfil = Perfil(
            empresa_id=emp.id,
            nombre="Cap y HWO",
            modulos=["capacitacion", "hwo"],
        )
        db.session.add(perfil)
        db.session.flush()
        u = Usuario(
            empresa_id=emp.id,
            email="restr@test.com",
            nombre="Restringido",
            rol="angel",
            perfil_id=perfil.id,
        )
        u.set_password("x")
        db.session.add(u)
        db.session.commit()
        assert codigos_modulos_permitidos(u) == {"capacitacion", "hwo"}
        uid = str(u.id)

    with client.session_transaction() as sess:
        sess["_user_id"] = uid
        sess["_fresh"] = True

    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert b"/gos/capacitacion/" in r.data
    assert b"/gos/hwo/" in r.data
    assert b"/gos/objetivos/" not in r.data
    assert b"/gos/vacaciones/" not in r.data

    r = client.get("/gos/objetivos/dashboard/", follow_redirects=False)
    assert r.status_code == 403


def test_perfil_no_eliminar_con_usuarios(auth_client, app):
    auth_client.post(
        "/perfiles/",
        data={"nombre": "En uso", "modulos": ["vacaciones"]},
        follow_redirects=True,
    )

    with app.app_context():
        from gos.models import Perfil

        perfil = Perfil.query.filter_by(nombre="En uso").first()

    auth_client.post(
        "/usuarios/",
        data={
            "email": "usa-perfil@test.com",
            "nombre": "Usuario Perfil",
            "password": "clave123",
            "rol": "usuario",
            "perfil_id": str(perfil.id),
        },
        follow_redirects=True,
    )

    r = auth_client.post(
        f"/perfiles/{perfil.id}/eliminar",
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"No se puede eliminar" in r.data
