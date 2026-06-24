def test_health(client):
    r = client.get("/gos/objetivos/api/v1/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


def test_login_redirect(client):
    r = client.get("/gos/objetivos/dashboard/")
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_login_page(client):
    r = client.get("/auth/login", follow_redirects=False)
    assert r.status_code == 200
    assert b"Ingresar" in r.data or b"email" in r.data.lower()


def test_login_ok(client, app):
    from gos.models import Usuario

    with app.app_context():
        user = Usuario.query.filter_by(email="t@test.com").first()
        assert user is not None
    r = client.post(
        "/auth/login",
        data={"email": "t@test.com", "password": "x"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.location.endswith("/") or "gos" in r.location
