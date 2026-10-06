import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_simulations():
    resp = client.get("/api/v1/simulations")
    assert resp.status_code == 200
    sims = resp.json()
    assert isinstance(sims, list)
    assert len(sims) >= 2 # Kapitalbank va Uzum

def test_get_simulation_detail():
    resp = client.get("/api/v1/simulations/kapitalbank-credit-analyst")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "kapitalbank-credit-analyst"
    assert "tasks" in data
    assert len(data["tasks"]) >= 1
    assert data["company"]["name"] == "Kapitalbank ATB"

def test_simulation_not_found():
    resp = client.get("/api/v1/simulations/non-existent-simulation")
    assert resp.status_code == 404
