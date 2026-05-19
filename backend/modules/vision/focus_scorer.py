import logging
import numpy as np
from collections import deque
from scipy.spatial.distance import euclidean

logger = logging.getLogger(__name__)

EAR_THRESHOLD_ATTENTIVE = 0.3
EAR_THRESHOLD_DROWSY = 0.2
SLIDING_WINDOW_SIZE = 10
BLINK_CONSECUTIVE_FRAMES = 3


def calculate_ear(eye_points: np.ndarray) -> float:
    """计算单眼的Eye Aspect Ratio

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    vertical_1 = euclidean(eye_points[1], eye_points[5])
    vertical_2 = euclidean(eye_points[2], eye_points[4])
    horizontal = euclidean(eye_points[0], eye_points[3])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


class FocusScorer:
    """专注度评分器：多因子加权 + 滑动窗口 + 眨眼检测"""

    def __init__(self, window_size: int = SLIDING_WINDOW_SIZE,
                 eye_weight: float = 0.4,
                 head_weight: float = 0.3,
                 body_weight: float = 0.3):
        self.window_size = window_size
        self.eye_weight = eye_weight
        self.head_weight = head_weight
        self.body_weight = body_weight
        self.ear_history = deque(maxlen=window_size)
        self.score_history = deque(maxlen=window_size)
        self.blink_counter = 0
        self.blink_total = 0
        self.frame_count = 0
        logger.info(f"专注度评分器初始化: window={window_size}, "
                     f"weights=({eye_weight}, {head_weight}, {body_weight})")

    def calculate_focus_score(self, ear_left: float, ear_right: float,
                              head_pose: dict = None,
                              body_pose: dict = None) -> dict:
        """计算综合专注度评分

        参数:
            ear_left: 左眼EAR值
            ear_right: 右眼EAR值
            head_pose: {"pitch": float, "yaw": float, "roll": float}
            body_pose: {"label": str, "score": float}

        返回:
            {"score": float, "label": str, "ear_avg": float,
             "eye_score": float, "head_score": float, "body_score": float,
             "blink_detected": bool, "blink_count": int}
        """
        self.frame_count += 1
        avg_ear = (ear_left + ear_right) / 2.0
        self.ear_history.append(avg_ear)

        blink_detected = self._detect_blink(ear_left, ear_right)

        eye_score = self._calc_eye_score(ear_left, ear_right)
        head_score = self._calc_head_score(head_pose)
        body_score = self._calc_body_score(body_pose)

        total_score = (eye_score * self.eye_weight +
                       head_score * self.head_weight +
                       body_score * self.body_weight)
        total_score = max(0, min(100, total_score))

        if len(self.score_history) > 0:
            smoothed = 0.7 * total_score + 0.3 * self.score_history[-1]
            total_score = smoothed

        self.score_history.append(total_score)

        label = self._score_to_label(total_score)

        return {
            "score": round(total_score, 1),
            "label": label,
            "ear_avg": round(avg_ear, 3),
            "eye_score": round(eye_score, 1),
            "head_score": round(head_score, 1),
            "body_score": round(body_score, 1),
            "blink_detected": blink_detected,
            "blink_count": self.blink_total
        }

    def _detect_blink(self, ear_left: float, ear_right: float) -> bool:
        """眨眼检测：连续N帧EAR低于阈值计为一次眨眼"""
        avg_ear = (ear_left + ear_right) / 2.0
        if avg_ear < EAR_THRESHOLD_DROWSY:
            self.blink_counter += 1
        else:
            if self.blink_counter >= BLINK_CONSECUTIVE_FRAMES:
                self.blink_total += 1
                logger.debug(f"检测到眨眼，累计: {self.blink_total}")
            self.blink_counter = 0
        return self.blink_counter >= BLINK_CONSECUTIVE_FRAMES

    def _calc_eye_score(self, ear_left: float, ear_right: float) -> float:
        """眼部评分：基于EAR值"""
        avg_ear = (ear_left + ear_right) / 2.0
        if len(self.ear_history) >= 3:
            recent = list(self.ear_history)[-3:]
            avg_ear = sum(recent) / len(recent)

        if avg_ear >= EAR_THRESHOLD_ATTENTIVE:
            return 100
        elif avg_ear >= 0.25:
            return 75
        elif avg_ear >= EAR_THRESHOLD_DROWSY:
            return 40
        else:
            return 10

    def _calc_head_score(self, head_pose: dict) -> float:
        """头部姿态评分"""
        if head_pose is None:
            return 70
        pitch = head_pose.get("pitch", 0)
        yaw = head_pose.get("yaw", 0)
        if abs(pitch) < 15 and abs(yaw) < 15:
            return 100
        elif abs(pitch) < 25 and abs(yaw) < 25:
            return 60
        else:
            return 20

    def _calc_body_score(self, body_pose: dict) -> float:
        """身体姿态评分"""
        if body_pose is None:
            return 70
        label = body_pose.get("label", "正常")
        score_map = {"正常": 100, "前倾": 50, "趴桌": 10, "离座": 0}
        return score_map.get(label, 70)

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

    def get_blink_rate(self) -> float:
        """获取每分钟眨眼频率"""
        if self.frame_count < 10:
            return 0.0
        fps_estimate = 15
        minutes = self.frame_count / (fps_estimate * 60)
        if minutes < 0.01:
            return 0.0
        return self.blink_total / minutes

    def reset(self):
        """重置所有状态"""
        self.ear_history.clear()
        self.score_history.clear()
        self.blink_counter = 0
        self.blink_total = 0
        self.frame_count = 0


def calculate_focus_score(ear_left: float, ear_right: float,
                          head_pose: dict = None,
                          body_pose: dict = None) -> dict:
    """便捷函数：计算专注度评分（无状态）"""
    scorer = FocusScorer()
    return scorer.calculate_focus_score(ear_left, ear_right, head_pose, body_pose)


def test():
    """专注度评分模块测试"""
    print("=== 专注度评分模块测试 ===")
    scorer = FocusScorer()

    test_cases = [
        ("正常睁眼", 0.35, 0.33, None, None),
        ("闭眼/疲劳", 0.15, 0.14, None, None),
        ("轻微低头", 0.28, 0.27, {"pitch": -20, "yaw": 5}, None),
        ("趴桌", 0.30, 0.29, None, {"label": "趴桌"}),
        ("转头", 0.32, 0.31, {"pitch": 0, "yaw": 30}, None),
        ("正常+身体正常", 0.35, 0.34, {"pitch": 5, "yaw": -3}, {"label": "正常"}),
    ]

    for name, ear_l, ear_r, head, body in test_cases:
        result = scorer.calculate_focus_score(ear_l, ear_r, head, body)
        print(f"  {name}: score={result['score']}, label={result['label']}, "
              f"ear_avg={result['ear_avg']}, blink={result['blink_detected']}")

    print(f"  累计眨眼次数: {scorer.blink_total}")
    print(f"  眨眼频率: {scorer.get_blink_rate():.1f} 次/分钟")
    print("[OK] 专注度评分模块测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
