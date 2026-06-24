def test_usuarios_requiere_admin(client):
    r = client.get("/usuarios/", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_usuarios_lista_admin(auth_client):
    r = auth_client.get("/usuarios/")
    assert r.status_code == 200
    assert b"Usuarios de la plataforma" in r.data
    assert b"t@test.com" in r.data


def test_usuarios_crear(auth_client, app):
    r = auth_client.post(
        "/usuarios/",
        data={
            "email": "nuevo@test.com",
            "nombre": "Usuario Nuevo",
            "password": "clave123",
            "rol": "usuario",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"creado correctamente" in r.data

    with app.app_context():
        from gos.models import Usuario

        user = Usuario.query.filter_by(email="nuevo@test.com").first()
        assert user is not None
        assert user.nombre == "Usuario Nuevo"
        assert user.rol == "usuario"
        assert user.es_usuario()
        assert user.check_password("clave123")


def test_usuarios_login_nuevo(client, app, auth_client):
    auth_client.post(
        "/usuarios/",
        data={
            "email": "oper@test.com",
            "nombre": "Operador",
            "password": "oper1234",
            "rol": "angel",
        },
        follow_redirects=True,
    )

    with client.session_transaction() as sess:
        sess.clear()

    r = client.post(
        "/auth/login",
        data={"email": "oper@test.com", "password": "oper1234"},
        follow_redirects=False,
    )
    assert r.status_code == 302


def test_roles_nuevos(app):
    with app.app_context():
        from gos.models import Empresa, Usuario
        from gos.models.usuario import ROLES

        assert ROLES == ("administrador", "usuario", "cliente", "angel")
        emp = Empresa.query.first()
        cliente = Usuario(
            empresa_id=emp.id,
            email="cli@test.com",
            nombre="Cliente",
            rol="cliente",
        )
        cliente.set_password("x")
        assert cliente.es_cliente()
        assert cliente.es_solo_lectura()
