import pytest

from app import create_app
from app.extensions import db
from app.models import Empresa, PlaneamientoConfig, Usuario


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        emp = Empresa(nombre="Test Co")
        db.session.add(emp)
        db.session.flush()
        db.session.add(PlaneamientoConfig(empresa_id=emp.id))
        u = Usuario(empresa_id=emp.id, email="t@test.com", nombre="Test", rol="admin")
        u.set_password("x")
        db.session.add(u)
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    with app.app_context():
        uid = str(Usuario.query.first().id)
    with client.session_transaction() as sess:
        sess["_user_id"] = uid
        sess["_fresh"] = True
    return client
