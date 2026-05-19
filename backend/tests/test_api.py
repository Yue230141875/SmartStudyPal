import pytest


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "SmartStudyPal" in data["message"]


def test_vision_status(client):
    response = client.get("/api/vision/status")
    assert response.status_code == 200


def test_vision_config(client):
    response = client.get("/api/vision/config")
    assert response.status_code == 200


def test_vision_start_stop(client):
    response = client.post("/api/vision/start")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    response = client.post("/api/vision/stop")
    assert response.status_code == 200


def test_pomodoro_session_start(client):
    response = client.post("/api/pomodoro/session/start", json={"user_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "session_id" in data["data"]


def test_pomodoro_start(client):
    response = client.post("/api/pomodoro/pomodoro/start", json={
        "user_id": 1,
        "task_name": "测试任务",
        "planned_duration": 1500,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_pomodoro_today_stats(client):
    response = client.get("/api/pomodoro/pomodoro/today-stats", params={"user_id": 1})
    assert response.status_code == 200


def test_pomodoro_fuse(client):
    response = client.post("/api/pomodoro/fuse", params={"vision_score": 80, "voice_emotion": "专注"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_dashboard_overview(client):
    response = client.get("/api/dashboard/overview", params={"user_id": 1})
    assert response.status_code == 200


def test_dashboard_weekly(client):
    response = client.get("/api/dashboard/weekly-focus", params={"user_id": 1})
    assert response.status_code == 200


def test_health_services(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
