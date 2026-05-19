import pytest
from modules.fusion_engine import FusionEngine, EMOTION_SCORE_MAP


def test_normal_fusion():
    engine = FusionEngine()
    result = engine.fuse(85, "专注")
    assert result["fused_score"] > 0
    assert result["label"] in ("专注", "轻度分心", "明显走神", "疲劳")
    assert result["conflict"] is False


def test_conflict_detection():
    engine = FusionEngine()
    result = engine.fuse(90, "烦躁")
    assert result["conflict"] is True
    assert "视觉专注但语音消极" in result["conflict_type"]


def test_conflict_voice_positive():
    engine = FusionEngine()
    result = engine.fuse(20, "专注")
    assert result["conflict"] is True
    assert "语音积极但视觉分心" in result["conflict_type"]


def test_score_clamping():
    engine = FusionEngine()
    result = engine.fuse(150, "专注")
    assert result["fused_score"] <= 100

    result = engine.fuse(-50, "专注")
    assert result["fused_score"] >= 0


def test_trend_calculation():
    engine = FusionEngine()
    for i in range(10):
        engine.fuse(60 + i * 2, "专注")

    trend = engine.get_trend()
    assert trend["direction"] in ("improving", "declining", "stable")
    assert trend["avg_score"] > 0


def test_emotion_score_map():
    assert EMOTION_SCORE_MAP["专注"] == 90
    assert EMOTION_SCORE_MAP["疲惫"] == 20
    assert EMOTION_SCORE_MAP.get("未知", 50) == 50


def test_reset():
    engine = FusionEngine()
    engine.fuse(80, "专注")
    engine.fuse(70, "平静")
    engine.reset()
    trend = engine.get_trend()
    assert trend["avg_score"] == 0


def test_custom_weights():
    engine = FusionEngine(vision_weight=0.5, voice_weight=0.5)
    result = engine.fuse(80, "平静")
    assert result["weights"]["vision"] == 0.5
    assert result["weights"]["voice"] == 0.5
