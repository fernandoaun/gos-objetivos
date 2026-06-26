import json

import pytest

from gos.modulos.hwo.database import DATA_DIR, init_db, reset_for_tests
from gos.modulos.hwo import storage


@pytest.fixture(autouse=True)
def hwo_db(app):
    reset_for_tests()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    reset_for_tests()


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


def test_hwo_save_and_load_dataset():
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


def test_hwo_modalidad_persiste():
    storage.save_modalidad({"EQ-1": "24hs", "EQ-2": "lun-vie"})
    prefs = storage.get_all_modalidad()
    assert prefs == {"EQ-1": "24hs", "EQ-2": "lun-vie"}


def test_hwo_migra_json_legacy_a_sqlite(tmp_path):
    reset_for_tests()
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
    import gos.modulos.hwo.database as db_mod

    old_data_dir = db_mod.DATA_DIR
    old_db_path = db_mod.DB_PATH
    old_st_data = st.DATA_DIR
    try:
        db_mod.DATA_DIR = data_dir
        db_mod.DB_PATH = data_dir / "hwo.db"
        st.DATA_DIR = data_dir
        st.DATASETS_FILE = data_dir / "datasets.json"
        st.MODALIDAD_FILE = data_dir / "modalidad.json"
        db_mod.reset_for_tests()
        st.migrate_legacy_data_if_empty()

        listed = st.get_all_datasets()
        assert len(listed) == 1
        assert listed[0]["name"] == "legacy"
        assert st.get_all_modalidad() == {"EQ-X": "12hs"}
    finally:
        db_mod.DATA_DIR = old_data_dir
        db_mod.DB_PATH = old_db_path
        st.DATA_DIR = old_st_data
        st.DATASETS_FILE = old_st_data / "datasets.json"
        st.MODALIDAD_FILE = old_st_data / "modalidad.json"


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

    r = auth_client.get("/gos/hwo/api/datasets/api-test")
    assert r.status_code == 200
    assert r.get_json()["rowsRaw"] == payload["rowsRaw"]
