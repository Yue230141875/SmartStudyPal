import logging
import numpy as np
from collections import deque
from scipy.spatial.distance import euclidean

logger = logging.getLogger(__name__)

EAR_THRESHOLD_ATTENTIVE = 0.25
EAR_THRESHOLD_DROWSY = 0.18
SLIDING_WINDOW_SIZE = 10
BLINK_CONSECUTIVE_FRAMES = 3


def calculate_ear(eye_points: np.ndarray) -> float:
    vertical_1 = euclidean(eye_points[1], eye_points[5])
    vertical_2 = euclidean(eye_points[2], eye_points[4])
    horizontal = euclidean(eye_points[0], eye_points[3])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


class FocusScorer:

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
        self.face_x_history = deque(maxlen=15)
        self.baseline_x = None
        self.blink_counter = 0
        self.blink_total = 0
        self.frame_count = 0
        logger.info(f"专注度评分器初始化: window={window_size}, "
                     f"weights=({eye_weight}, {head_weight}, {body_weight})")

    def calculate_focus_score(self, ear_left: float, ear_right: float,
                              head_pose: dict = None,
                              body_pose: dict = None,
                              face_rect: tuple = None,
                              frame_shape: tuple = None) -> dict:
        self.frame_count += 1
        avg_ear = (ear_left + ear_right) / 2.0
        self.ear_history.append(avg_ear)

        self._update_baseline(face_rect, frame_shape)

        blink_detected = self._detect_blink(ear_left, ear_right)

        eye_score = self._calc_eye_score(ear_left, ear_right)
        head_score = self._calc_head_score(head_pose, face_rect, frame_shape)
        body_score = self._calc_body_score(body_pose)

        if head_pose is not None:
            yaw_mag = abs(head_pose.get("yaw", 0))
            if yaw_mag >= 50:
                eye_score = min(eye_score, 30)
            elif yaw_mag >= 35:
                eye_score = min(eye_score, 55)
            elif yaw_mag >= 25:
                eye_score = min(eye_score, 75)

        total_score = (eye_score * self.eye_weight +
                       head_score * self.head_weight +
                       body_score * self.body_weight)
        total_score = max(0, min(100, total_score))

        if len(self.score_history) > 0:
            smoothed = 0.5 * total_score + 0.5 * self.score_history[-1]
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

    def _update_baseline(self, face_rect: tuple, frame_shape: tuple):
        if face_rect is None or frame_shape is None:
            return
        try:
            w = frame_shape[1]
            fx, fy, fw, fh = face_rect
            center_x = (fx + fw / 2) / w
            self.face_x_history.append(center_x)
            if len(self.face_x_history) >= 8 and self.baseline_x is None:
                vals = list(self.face_x_history)
                self.baseline_x = np.median(vals)
                logger.debug(f"人脸基准位置建立: {self.baseline_x:.3f}")
        except Exception:
            pass

    def _detect_blink(self, ear_left: float, ear_right: float) -> bool:
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
        avg_ear = (ear_left + ear_right) / 2.0
        if len(self.ear_history) >= 3:
            recent = list(self.ear_history)[-3:]
            avg_ear = sum(recent) / len(recent)

        if avg_ear >= EAR_THRESHOLD_ATTENTIVE:
            return 100
        elif avg_ear >= 0.20:
            return 80
        elif avg_ear >= EAR_THRESHOLD_DROWSY:
            return 50
        else:
            return 15

    def _calc_head_score(self, head_pose: dict, face_rect: tuple = None,
                         frame_shape: tuple = None) -> float:

        if head_pose is None:
            return 80

        pitch = head_pose.get("pitch", 0)
        yaw = head_pose.get("yaw", 0)

        yaw_score = 100
        if abs(yaw) < 20:
            yaw_score = 100
        elif abs(yaw) < 35:
            yaw_score = 75
        elif abs(yaw) < 50:
            yaw_score = 45
        else:
            yaw_score = 20

        pitch_score = 100
        if -45 <= pitch <= 10:
            pitch_score = 100
        elif -60 <= pitch < -45:
            pitch_score = 80
        elif 10 < pitch <= 25:
            pitch_score = 70
        elif pitch > 25:
            pitch_score = 40
        elif pitch < -60:
            pitch_score = 50

        base_score = yaw_score * 0.6 + pitch_score * 0.4

        return base_score

    def _face_offset_severity(self, face_rect: tuple, frame_shape: tuple):
        if face_rect is None or frame_shape is None:
            return None
        try:
            w = frame_shape[1]
            fx, fy, fw, fh = face_rect
            face_center_x = (fx + fw / 2) / w

            if self.baseline_x is not None:
                rel_offset = abs(face_center_x - self.baseline_x)
                if rel_offset > 0.22:
                    return "large"
                elif rel_offset > 0.15:
                    return "medium"
                else:
                    return None
            else:
                return None
        except Exception:
            return None

    def _calc_body_score(self, body_pose: dict) -> float:
        if body_pose is None:
            return 80
        label = body_pose.get("label", "正常")
        score_map = {"正常": 100, "前倾": 70, "趴桌": 20, "离座": 0}
        return score_map.get(label, 80)

    def _score_to_label(self, score: float) -> str:
        if score >= 65:
            return "专注"
        elif score >= 45:
            return "轻度分心"
        elif score >= 25:
            return "明显走神"
        else:
            return "疲劳"

    def get_blink_rate(self) -> float:
        if self.frame_count < 10:
            return 0.0
        fps_estimate = 15
        minutes = self.frame_count / (fps_estimate * 60)
        if minutes < 0.01:
            return 0.0
        return self.blink_total / minutes

    def reset(self):
        self.ear_history.clear()
        self.score_history.clear()
        self.face_x_history.clear()
        self.baseline_x = None
        self.blink_counter = 0
        self.blink_total = 0
        self.frame_count = 0


def calculate_focus_score(ear_left: float, ear_right: float,
                          head_pose: dict = None,
                          body_pose: dict = None,
                          face_rect: tuple = None,
                          frame_shape: tuple = None) -> dict:
    scorer = FocusScorer()
    return scorer.calculate_focus_score(ear_left, ear_right, head_pose, body_pose,
                                        face_rect, frame_shape)


def test():
    print("=== 专注度评分模块测试 ===")
    scorer = FocusScorer()

    test_cases = [
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (220, 80, 200, 280), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (225, 85, 195, 275), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (218, 82, 202, 278), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (222, 78, 198, 282), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (220, 80, 200, 280), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (223, 83, 197, 277), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (219, 79, 201, 281), (480, 640)),
        ("正视居中(基准)", 0.34, 0.33, {"pitch": -5, "yaw": 3}, {"label": "正常"}, (221, 81, 199, 279), (480, 640)),
        ("向左偏头", 0.32, 0.31, {"pitch": 0, "yaw": 5}, {"label": "正常"}, (80, 90, 180, 270), (480, 640)),
        ("向右偏头", 0.32, 0.31, {"pitch": 0, "yaw": -5}, {"label": "正常"}, (360, 90, 180, 270), (480, 640)),
        ("大幅左转", 0.30, 0.29, {"pitch": 0, "yaw": 35}, {"label": "正常"}, (60, 90, 170, 270), (480, 640)),
        ("大幅右转", 0.30, 0.29, {"pitch": 0, "yaw": -35}, {"label": "正常"}, (380, 90, 170, 270), (480, 640)),
        ("极左转", 0.28, 0.27, {"pitch": 0, "yaw": 55}, {"label": "正常"}, (20, 90, 160, 270), (480, 640)),
        ("极右转", 0.28, 0.27, {"pitch": 0, "yaw": -55}, {"label": "正常"}, (420, 90, 160, 270), (480, 640)),
    ]

    for name, ear_l, ear_r, head, body, rect, shape in test_cases:
        result = scorer.calculate_focus_score(ear_l, ear_r, head, body, rect, shape)
        print(f"  {name}: score={result['score']}, label={result['label']}, "
              f"head={result['head_score']}")

    print("[OK] 专注度评分模块测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
