import pytest

from app.data.synthetic import generate_dataset
from app.main import create_app
from app.service import BatteryService


@pytest.fixture(scope="session")
def cycles():
    return generate_dataset(n_cycles=80)


@pytest.fixture(scope="session")
def service():
    svc = BatteryService(data_dir=None)
    svc.cycles = generate_dataset(n_cycles=80)
    return svc


@pytest.fixture(scope="session")
def trained_service(service):
    service.train(evaluate=False)
    return service


@pytest.fixture()
def client(trained_service):
    from fastapi.testclient import TestClient

    return TestClient(create_app(trained_service))


@pytest.fixture()
def untrained_client():
    from fastapi.testclient import TestClient

    svc = BatteryService(data_dir=None)
    svc.cycles = generate_dataset(n_cycles=40)
    return TestClient(create_app(svc))
