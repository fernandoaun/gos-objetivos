def test_cambiar_contrasena_requiere_login(client):
    r = client.get("/auth/cambiar-contrasena", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_cambiar_contrasena_form(auth_client):
    r = auth_client.get("/auth/cambiar-contrasena")
    assert r.status_code == 200
    assert b"Cambiar contrase" in r.data


def test_cambiar_contrasena_actual_incorrecta(auth_client):
    r = auth_client.post(
        "/auth/cambiar-contrasena",
        data={
            "actual": "incorrecta",
            "nueva": "nueva123",
            "confirmacion": "nueva123",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"no es correcta" in r.data


def test_cambiar_contrasena_confirmacion_distinta(auth_client):
    r = auth_client.post(
        "/auth/cambiar-contrasena",
        data={
            "actual": "x",
            "nueva": "nueva123",
            "confirmacion": "otra123",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"no coincide" in r.data


def test_cambiar_contrasena_ok(client, app, auth_client):
    r = auth_client.post(
        "/auth/cambiar-contrasena",
        data={
            "actual": "x",
            "nueva": "clave456",
            "confirmacion": "clave456",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"actualizada correctamente" in r.data

    with client.session_transaction() as sess:
        sess.clear()

    r = client.post(
        "/auth/login",
        data={"email": "t@test.com", "password": "clave456"},
        follow_redirects=False,
    )
    assert r.status_code == 302

    with app.app_context():
        from gos.models import Usuario

        user = Usuario.query.filter_by(email="t@test.com").first()
        assert user.check_password("clave456")
