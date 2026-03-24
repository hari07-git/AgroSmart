from __future__ import annotations

from pathlib import Path

import pytest

from agrosmart import create_app
from agrosmart.db import db


@pytest.fixture()
def app(tmp_path: Path):
    database_path = tmp_path / "test.sqlite3"
    upload_path = tmp_path / "uploads"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "UPLOAD_FOLDER": upload_path,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test",
            "REQUIRE_EMAIL_OTP": False,
        }
    )
    with app.app_context():
        db.create_all()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _register_and_login(client):
    res = client.post(
        "/auth/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password",
            "password_confirm": "password",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200


def test_register_login_and_dashboard(client):
    _register_and_login(client)
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 200
    assert "Choose a service" in res.get_data(as_text=True)


def test_crop_api_requires_login(client):
    res = client.post("/api/crop/predict", json={"nitrogen": 1})
    assert res.status_code in (302, 401, 403)


def test_crop_api_after_login(client):
    _register_and_login(client)
    res = client.post(
        "/api/crop/predict",
        json={
            "nitrogen": 80,
            "phosphorus": 40,
            "potassium": 35,
            "temperature": 28,
            "humidity": 72,
            "rainfall": 180,
            "ph": 6.5,
            "season": "Kharif",
        },
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert "predicted_crop" in payload


def test_fertilizer_api_after_login(client):
    _register_and_login(client)
    res = client.post(
        "/api/fertilizer/recommend",
        json={"crop_name": "Rice", "nitrogen": 10, "phosphorus": 10, "potassium": 10},
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["crop"]
    assert "usage_instructions" in payload


def test_disease_api_requires_file(client):
    _register_and_login(client)
    res = client.post("/api/disease/predict", data={})
    assert res.status_code == 400


def test_my_history_csv_export(client):
    _register_and_login(client)
    res = client.get("/services/me/export.csv")
    assert res.status_code == 200
    assert "CROP_PREDICTIONS" in res.get_data(as_text=True)


def test_admin_forbidden_for_non_admin(client):
    _register_and_login(client)
    res = client.get("/admin/")
    assert res.status_code == 302
    assert "/admin/login" in res.headers.get("Location", "")


def test_language_switch_hindi(client):
    res = client.get("/?lang=hi")
    # Login link should be translated on public home page.
    assert "लॉगिन" in res.get_data(as_text=True)


def test_weather_requires_key_or_errors(client):
    _register_and_login(client)
    res = client.get("/api/weather/current")
    assert res.status_code == 400


def test_member_can_delete_own_crop_prediction(app, client):
    _register_and_login(client)
    client.post(
        "/api/crop/predict",
        json={
            "nitrogen": 80,
            "phosphorus": 40,
            "potassium": 35,
            "temperature": 28,
            "humidity": 72,
            "rainfall": 180,
            "ph": 6.5,
            "season": "Kharif",
        },
    )
    from agrosmart.models import CropPrediction
    from agrosmart.db import db

    with app.app_context():
        pred = CropPrediction.query.order_by(CropPrediction.id.desc()).first()
        assert pred is not None
        pred_id = pred.id

    res = client.post(f"/services/crop/delete/{pred_id}", follow_redirects=True)
    assert res.status_code == 200


def test_member_can_delete_own_fertilizer_record(app, client):
    _register_and_login(client)
    client.post(
        "/api/fertilizer/recommend",
        json={"crop_name": "Rice", "nitrogen": 10, "phosphorus": 10, "potassium": 10},
    )
    from agrosmart.models import FertilizerRecommendation

    with app.app_context():
        rec = FertilizerRecommendation.query.order_by(FertilizerRecommendation.id.desc()).first()
        assert rec is not None
        rec_id = rec.id

    res = client.post(f"/services/fertilizer/delete/{rec_id}", follow_redirects=True)
    assert res.status_code == 200
