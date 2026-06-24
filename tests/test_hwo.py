def test_hwo_health_requires_auth(client):
    r = client.get("/gos/hwo/api/health")
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_hwo_health_ok(auth_client):
    r = auth_client.get("/gos/hwo/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


def test_hwo_shell(auth_client):
    r = auth_client.get("/gos/hwo/")
    assert r.status_code == 200
    assert b"hwo-frame" in r.data


def test_hwo_app(auth_client):
    r = auth_client.get("/gos/hwo/app/")
    assert r.status_code == 200
    assert b"Dashboard HWO" in r.data
