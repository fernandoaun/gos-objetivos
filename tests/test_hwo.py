import json

import pytest

from gos.modulos.hwo.database import DATA_DIR
from gos.modulos.hwo import storage


@pytest.fixture(autouse=True)
def hwo_db(app):
    with app.app_context():
        storage.reset_for_tests()
        yield
        storage.reset_for_tests()


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


def test_hwo_save_and_load_dataset(app):
    with app.app_context():
        config = {"periodStart": 1, "periodEnd": 2, "eqs": {}}
        rows = [{"fecha": 1000, "equipo": "A"}]
        storage.save_dataset("test-ds", config, rows)

        listed = storage.get_all_datasets()
        assert len(listed) == 1
        assert listed[0]["name"] == "test-ds"
        assert listed[0]["row_count"] == 1

        loaded = storage.get_dataset("test-ds")
        assert loaded is not None
        assert loaded["name"] == "test-ds"
        assert loaded["configRaw"] == config
        assert loaded["rowsRaw"] == rows


def test_hwo_modalidad_persiste(app):
    with app.app_context():
        storage.save_modalidad({"EQ-1": "24hs", "EQ-2": "lun-vie"})
        prefs = storage.get_all_modalidad()
        assert prefs == {"EQ-1": "24hs", "EQ-2": "lun-vie"}


def test_hwo_modalidad_actualiza_sin_borrar_otros(app):
    with app.app_context():
        storage.save_modalidad({"EQ-1": "24hs", "EQ-2": "lun-vie"})
        storage.save_modalidad({"EQ-1": "12hs"})
        prefs = storage.get_all_modalidad()
        assert prefs == {"EQ-1": "12hs", "EQ-2": "lun-vie"}


def test_hwo_migra_json_legacy_a_db(app, tmp_path):
    with app.app_context():
        storage.reset_for_tests()
        data_dir = tmp_path / "hwo"
        data_dir.mkdir()
        datasets = {
            "legacy": {
                "name": "legacy",
                "savedAt": 1234567890000,
                "configRaw": {"periodStart": None},
                "rowsRaw": [{"fecha": 1}],
            }
        }
        (data_dir / "datasets.json").write_text(json.dumps(datasets), encoding="utf-8")
        (data_dir / "modalidad.json").write_text(
            json.dumps({"EQ-X": "12hs"}), encoding="utf-8"
        )

        import gos.modulos.hwo.storage as st

        old_data = st.DATA_DIR
        old_datasets = st.DATASETS_FILE
        old_modalidad = st.MODALIDAD_FILE
        try:
            st.DATA_DIR = data_dir
            st.DATASETS_FILE = data_dir / "datasets.json"
            st.MODALIDAD_FILE = data_dir / "modalidad.json"
            app.config["TESTING"] = False
            st.migrate_legacy_data_if_empty()

            listed = st.get_all_datasets()
            assert len(listed) == 1
            assert listed[0]["name"] == "legacy"
            assert st.get_all_modalidad() == {"EQ-X": "12hs"}
        finally:
            app.config["TESTING"] = True
            st.DATA_DIR = old_data
            st.DATASETS_FILE = old_datasets
            st.MODALIDAD_FILE = old_modalidad


def test_hwo_api_datasets(auth_client):
    payload = {
        "name": "api-test",
        "configRaw": {"periodStart": 1, "eqs": {}},
        "rowsRaw": [{"fecha": 500}],
    }
    r = auth_client.post("/gos/hwo/api/datasets", json=payload)
    assert r.status_code == 200

    r = auth_client.get("/gos/hwo/api/datasets")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "api-test"

    r = auth_client.get("/gos/hwo/api/datasets/by-name?name=api-test")
    assert r.status_code == 200
    assert r.get_json()["rowsRaw"] == payload["rowsRaw"]


def test_hwo_api_rename_dataset(app, auth_client):
    with app.app_context():
        storage.save_dataset("tab-vieja", {"eqs": {}}, [{"fecha": 1}])
        storage.save_modalidad({"tab-vieja|EQ-1": "24hs", "EQ-2": "lun-vie"})

    r = auth_client.put(
        "/gos/hwo/api/datasets/rename",
        json={"oldName": "tab-vieja", "newName": "tab-nueva"},
    )
    assert r.status_code == 200
    assert r.get_json()["name"] == "tab-nueva"

    with app.app_context():
        assert storage.get_dataset("tab-vieja") is None
        assert storage.get_dataset("tab-nueva") is not None
        prefs = storage.get_all_modalidad()
        assert prefs.get("tab-nueva|EQ-1") == "24hs"
        assert prefs.get("EQ-2") == "lun-vie"

    r2 = auth_client.put(
        "/gos/hwo/api/datasets/rename",
        json={"oldName": "tab-nueva", "newName": "tab-nueva"},
    )
    assert r2.status_code == 200


def test_hwo_api_dataset_nombre_con_caracteres_especiales(auth_client):
    from urllib.parse import urlencode

    name = "Ventas HW-SW · Hoja3"
    payload = {
        "name": name,
        "configRaw": {"periodStart": 1, "eqs": {}},
        "rowsRaw": [{"fecha": 100}],
    }
    r = auth_client.post("/gos/hwo/api/datasets", json=payload)
    assert r.status_code == 200

    r = auth_client.get("/gos/hwo/api/datasets/by-name?" + urlencode({"name": name}))
    assert r.status_code == 200
    assert r.get_json()["name"] == name
