import pytest
from modules.degradation_manager import DegradationManager, ServiceLevel


def test_initial_state():
    dm = DegradationManager()
    dm.register_service("vision")
    assert dm.get_service_level("vision") == ServiceLevel.FULL


def test_degradation_on_errors():
    dm = DegradationManager(max_errors=3)
    dm.register_service("vision")

    for i in range(3):
        dm.report_error("vision", f"error {i+1}")
    assert dm.get_service_level("vision") == ServiceLevel.DEGRADED

    for i in range(3):
        dm.report_error("vision", f"error {i+1}")
    assert dm.get_service_level("vision") == ServiceLevel.MINIMAL

    for i in range(3):
        dm.report_error("vision", f"error {i+1}")
    assert dm.get_service_level("vision") == ServiceLevel.OFFLINE


def test_recovery_on_success():
    dm = DegradationManager(max_errors=2, recovery_threshold=2)
    dm.register_service("vision")

    dm.report_error("vision", "error")
    dm.report_error("vision", "error")
    assert dm.get_service_level("vision") == ServiceLevel.DEGRADED

    dm.report_success("vision", "ok")
    dm.report_success("vision", "ok")
    assert dm.get_service_level("vision") == ServiceLevel.FULL


def test_fusion_weights_adjustment():
    dm = DegradationManager()
    dm.register_service("vision")
    dm.register_service("voice")

    weights = dm.get_fusion_weights()
    assert weights["vision"] == 0.7
    assert weights["voice"] == 0.3

    for i in range(5):
        dm.report_error("voice", "error")
    weights = dm.get_fusion_weights()
    assert weights["vision"] > weights["voice"]


def test_is_available():
    dm = DegradationManager(max_errors=2)
    dm.register_service("vision")

    assert dm.is_available("vision") is True

    dm.report_error("vision", "error")
    dm.report_error("vision", "error")
    assert dm.is_available("vision", min_level=ServiceLevel.FULL) is False
    assert dm.is_available("vision", min_level=ServiceLevel.MINIMAL) is True


def test_get_all_status():
    dm = DegradationManager()
    dm.register_service("vision")
    dm.register_service("voice")

    status = dm.get_all_status()
    assert "services" in status
    assert "fusion_weights" in status
    assert "overall" in status
    assert "vision" in status["services"]
