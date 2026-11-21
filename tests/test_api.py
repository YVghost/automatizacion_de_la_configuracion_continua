import os
import tempfile
from pathlib import Path
import pytest

temp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(temp.name) / "test.db").as_posix()
os.environ["ENABLE_LOAD_TEST"] = "true"

from fastapi.testclient import TestClient
from app.main import app, engine


@pytest.fixture(scope="session", autouse=True)
def cleanup_database():
    yield
    engine.dispose()
    temp.cleanup()


def test_complete_flow():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/ready").status_code == 200
        bike = client.post("/api/bikes", json={"owner": "Mateo Ortega", "name": "Trek Marlin", "category": "Montaña"})
        assert bike.status_code == 201
        bike_id = bike.json()["id"]
        photo = b"\x89PNG\r\n\x1a\n" + b"test"
        review = client.post("/api/reviews", data={"bike_id": bike_id, "accessory": "Casco", "comment": "Ligero y cómodo", "rating": 5}, files={"photo": ("casco.png", photo, "image/png")})
        assert review.status_code == 201
        assert client.get(f"/api/reviews/{review.json()['id']}/photo").content == photo
        assert client.get("/api/reviews").json()[0]["owner"] == "Mateo Ortega"
        assert client.get("/api/stats").json() == {"bikes": 1, "reviews": 1, "rating": 5.0}


def test_invalid_inputs():
    with TestClient(app) as client:
        assert client.post("/api/bikes", json={"owner": " ", "name": "Trek", "category": "Ruta"}).status_code == 422
        data = {"bike_id": 999999, "accessory": "Luz", "comment": "Buena luz", "rating": 5}
        assert client.post("/api/reviews", data=data).status_code == 404
        data["rating"] = 6
        assert client.post("/api/reviews", data=data).status_code == 422
        data["rating"] = 5
        assert client.post("/api/reviews", data=data, files={"photo": ("x.svg", b"<svg/>", "image/svg+xml")}).status_code == 422
        assert client.get("/api/reviews/999999/photo").status_code == 404


def test_load_endpoint_requires_opt_in():
    with TestClient(app) as client:
        os.environ["ENABLE_LOAD_TEST"] = "false"
        assert client.get("/api/demo/work").status_code == 404
        os.environ["ENABLE_LOAD_TEST"] = "true"
        assert client.get("/api/demo/work").status_code == 200
