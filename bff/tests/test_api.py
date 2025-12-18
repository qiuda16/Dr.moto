import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_auth_login():
    response = client.post(
        "/auth/token",
        data={"username": "staff", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_work_order_unauthorized():
    response = client.post(
        "/mp/workorders/create",
        json={"customer_id": "Test", "vehicle_plate": "TEST-000", "description": "Test"}
    )
    assert response.status_code == 401
