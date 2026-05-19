import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

EMOTION_SCORE_MAP = {
    "专注": 90,
    "平静": 80,
    "烦躁": 30,
    "疲惫": 20,
    "焦虑": 25,
    "未知": 50,
}

CONFLICT_THRESHOLD = 30


class FusionEngine:
    """多模态融合引擎：加权融合 + 冲突检测 + 滑动窗口"""

    def __init__(self, vision_weight: float = 0.7, voice_weight: float = 0.3,
                 window_size: int = 10):
        self.vision_weight = vision_weight
        self.voice_weight = voice_weight
        self.window_size = window_size
        self.score_history = deque(maxlen=window_size)
        self.conflict_count = 0
        self.frame_count = 0
        logger.info(f"融合引擎初始化: vision_w={vision_weight}, voice_w={voice_weight}, "
                     f"window={window_size}")

    def fuse(self, vision_score: float, voice_emotion: str,
             vision_weight: float = None, voice_weight: float = None) -> dict:
        """融合视觉和语音数据

        参数:
            vision_score: 视觉专注度评分 (0-100)
            voice_emotion: 语音情绪标签
            vision_weight: 视觉权重（覆盖默认值）
            voice_weight: 语音权重（覆盖默认值）

        返回:
            {"fused_score": float, "label": str, "conflict": bool,
             "conflict_type": str, "vision_score": float, "voice_score": float,
             "weights": dict}
        """
        self.frame_count += 1

        v_weight = vision_weight if vision_weight is not None else self.vision_weight
        vo_weight = voice_weight if voice_weight is not None else self.voice_weight

        total = v_weight + vo_weight
        if total > 0:
            v_weight /= total
            vo_weight /= total

        voice_score = EMOTION_SCORE_MAP.get(voice_emotion, 50)

        conflict = False
        conflict_type = ""
        score_diff = abs(vision_score - voice_score)
        if score_diff > CONFLICT_THRESHOLD:
            conflict = True
            self.conflict_count += 1
            if vision_score > voice_score + CONFLICT_THRESHOLD:
                conflict_type = "视觉专注但语音消极"
            elif voice_score > vision_score + CONFLICT_THRESHOLD:
                conflict_type = "语音积极但视觉分心"

        if conflict:
            fused_score = self._resolve_conflict(
                vision_score, voice_score, v_weight, vo_weight, conflict_type
            )
        else:
            fused_score = vision_score * v_weight + voice_score * vo_weight

        fused_score = max(0, min(100, fused_score))

        if len(self.score_history) > 0:
            smoothed = 0.7 * fused_score + 0.3 * self.score_history[-1]["fused_score"]
            fused_score = smoothed

        label = self._score_to_label(fused_score)

        result = {
            "fused_score": round(fused_score, 1),
            "label": label,
            "conflict": conflict,
            "conflict_type": conflict_type,
            "vision_score": round(vision_score, 1),
            "voice_score": voice_score,
            "voice_emotion": voice_emotion,
            "weights": {"vision": round(v_weight, 2), "voice": round(vo_weight, 2)},
            "timestamp": datetime.now().isoformat(),
        }

        self.score_history.append(result)
        return result

    def _resolve_conflict(self, vision_score: float, voice_score: float,
                          v_weight: float, vo_weight: float,
                          conflict_type: str) -> float:
        """冲突解决策略"""
        if "视觉专注但语音消极" in conflict_type:
            fused = vision_score * 0.8 + voice_score * 0.2
            logger.debug(f"冲突解决（视觉优先）: v={vision_score}, vo={voice_score} -> {fused:.1f}")
        elif "语音积极但视觉分心" in conflict_type:
            fused = vision_score * 0.85 + voice_score * 0.15
            logger.debug(f"冲突解决（视觉优先）: v={vision_score}, vo={voice_score} -> {fused:.1f}")
        else:
            fused = vision_score * v_weight + voice_score * vo_weight
        return fused

    def _score_to_label(self, score: float) -> str:
        """分数转标签"""
        if score >= 75:
            return "专注"
        elif score >= 50:
            return "轻度分心"
        elif score >= 25:
            return "明显走神"
        else:
            return "疲劳"

    def get_trend(self, n: int = 10) -> dict:
        """获取最近N帧的趋势"""
        if not self.score_history:
            return {"trend": "stable", "avg_score": 0, "direction": "none"}

        recent = list(self.score_history)[-n:]
        scores = [r["fused_score"] for r in recent]
        avg_score = sum(scores) / len(scores)

        if len(scores) >= 3:
            first_half = sum(scores[:len(scores) // 2]) / (len(scores) // 2)
            second_half = sum(scores[len(scores) // 2:]) / (len(scores) - len(scores) // 2)
            diff = second_half - first_half
            if diff > 5:
                direction = "improving"
            elif diff < -5:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "stable"

        return {
            "trend": direction,
            "avg_score": round(avg_score, 1),
            "direction": direction,
            "conflict_rate": round(self.conflict_count / max(self.frame_count, 1), 3),
        }

    def reset(self):
        """重置状态"""
        self.score_history.clear()
        self.conflict_count = 0
        self.frame_count = 0


def fuse_focus(vision_score: float, voice_emotion: str,
               vision_weight: float = 0.7, voice_weight: float = 0.3) -> dict:
    """便捷函数：融合视觉和语音数据"""
    engine = FusionEngine(vision_weight=vision_weight, voice_weight=voice_weight)
    return engine.fuse(vision_score, voice_emotion, vision_weight, voice_weight)


def test():
    """多模态融合引擎测试"""
    print("=== 多模态融合引擎测试 ===")
    engine = FusionEngine()

    test_cases = [
        ("正常融合-专注", 85, "专注"),
        ("正常融合-烦躁", 60, "烦躁"),
        ("正常融合-疲惫", 30, "疲惫"),
        ("冲突-视觉专注语音消极", 90, "烦躁"),
        ("冲突-语音积极视觉分心", 30, "专注"),
        ("平静状态", 70, "平静"),
    ]

    for name, v_score, emotion in test_cases:
        result = engine.fuse(v_score, emotion)
        print(f"  {name}: fused={result['fused_score']}, label={result['label']}, "
              f"conflict={result['conflict']}, type={result['conflict_type']}")

    trend = engine.get_trend()
    print(f"  趋势: {trend}")
    print("[OK] 多模态融合引擎测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
