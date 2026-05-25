import logging
import numpy as np
import cv2

logger = logging.getLogger(__name__)

_ImagePreprocessor = None
_FaceDetector = None
_DLIB_AVAILABLE = False
_FocusScorer = None
_PoseEstimator = None
_MP_AVAILABLE = False

try:
    from .image_preprocessor import ImagePreprocessor as _ImagePreprocessor
except ImportError as e:
    logger.warning(f"图像预处理模块导入失败: {e}")

try:
    from .face_detector import FaceDetector as _FaceDetector, _DLIB_AVAILABLE
except ImportError as e:
    logger.warning(f"人脸检测模块导入失败: {e}")

try:
    from .focus_scorer import FocusScorer as _FocusScorer
except ImportError as e:
    logger.warning(f"专注度评分模块导入失败: {e}")

try:
    from .pose_estimator import PoseEstimator as _PoseEstimator, _MP_AVAILABLE
except ImportError as e:
    logger.warning(f"姿态估计模块导入失败: {e}")

_DLIB_3D_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)


class VisionManager:
    """视觉模块统一管理器"""

    def __init__(self):
        self.preprocessor = _ImagePreprocessor() if _ImagePreprocessor else None
        self.face_detector = None
        self.pose_estimator = None
        self.focus_scorer = _FocusScorer() if _FocusScorer else None
        self._vision_available = False

        if _FaceDetector and _DLIB_AVAILABLE:
            try:
                self.face_detector = _FaceDetector()
                logger.info("人脸检测器初始化成功")
            except Exception as e:
                logger.warning(f"人脸检测器初始化失败: {e}")

        if _PoseEstimator and _MP_AVAILABLE:
            try:
                self.pose_estimator = _PoseEstimator()
                logger.info("姿态估计器初始化成功")
            except Exception as e:
                logger.warning(f"姿态估计器初始化失败: {e}，将使用dlib备用方案")

        self._vision_available = (self.face_detector is not None)
        if self._vision_available:
            if self.pose_estimator:
                logger.info("视觉模块初始化完成（完整功能：dlib + MediaPipe）")
            else:
                logger.info("视觉模块初始化完成（基础功能：dlib 备用方案）")
        else:
            logger.warning("视觉模块不可用：人脸检测器未初始化")

    def process_frame(self, frame) -> dict:
        """处理单帧图像，返回完整检测结果"""
        preprocessed = self.preprocessor.preprocess(frame) if self.preprocessor else frame

        face_result = {"face_detected": False, "landmarks_68": None,
                       "ear_left": 0.0, "ear_right": 0.0, "face_rect": None}
        if self.face_detector:
            det = self.face_detector.detect(preprocessed)
            face_result["face_detected"] = det["face_detected"]
            face_result["num_faces"] = det.get("num_faces", 0)
            face_result["face_rect"] = det.get("face_rect")
            if det["face_detected"] and det["landmarks_68"] is not None:
                left_eye, right_eye = self.face_detector.get_eye_points(det["landmarks_68"])
                face_result["ear_left"] = self.face_detector.calculate_ear(left_eye)
                face_result["ear_right"] = self.face_detector.calculate_ear(right_eye)
                face_result["landmarks_68"] = det["landmarks_68"]

        pose_result = {"head": {"pitch": 0, "yaw": 0, "roll": 0, "available": False},
                       "body": {"label": "离座", "score": 0, "available": False}}

        if self.pose_estimator:
            pose_result = self.pose_estimator.process_frame(preprocessed)

        if not pose_result["head"]["available"] and face_result["landmarks_68"] is not None:
            head_pose = self._estimate_head_pose_from_dlib(
                face_result["landmarks_68"], preprocessed.shape)
            pose_result["head"] = head_pose

        if not pose_result["body"]["available"] and face_result["face_detected"]:
            body_pose = self._estimate_body_pose_heuristic(
                face_result["face_rect"], preprocessed.shape)
            pose_result["body"] = body_pose

        if self.focus_scorer:
            focus_result = self.focus_scorer.calculate_focus_score(
                face_result["ear_left"], face_result["ear_right"],
                head_pose=pose_result["head"] if pose_result["head"]["available"] else None,
                body_pose=pose_result["body"] if pose_result["body"]["available"] else None,
                face_rect=face_result["face_rect"],
                frame_shape=preprocessed.shape,
            )
        else:
            focus_result = {
                "score": 0, "label": "未检测", "ear_avg": 0,
                "eye_score": 0, "head_score": 0, "body_score": 0,
                "blink_detected": False, "blink_count": 0,
            }

        return {
            "face_detected": face_result["face_detected"],
            "ear": {"left": face_result["ear_left"], "right": face_result["ear_right"]},
            "head_pose": pose_result["head"],
            "body_pose": pose_result["body"],
            "focus_score": focus_result["score"],
            "focus_level": focus_result["label"],
            "focus_color": self._score_to_color(focus_result["score"]),
            "eye_score": focus_result["eye_score"],
            "head_score": focus_result["head_score"],
            "body_score": focus_result["body_score"],
            "ear_avg": focus_result["ear_avg"],
            "blink_detected": focus_result["blink_detected"],
            "blink_count": focus_result["blink_count"],
            "vision_available": self._vision_available,
        }

    @staticmethod
    def _estimate_head_pose_from_dlib(landmarks_68: np.ndarray, frame_shape: tuple) -> dict:
        """使用 dlib 68点关键点 + solvePnP 估计头部姿态"""
        default_result = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "available": False}
        try:
            h, w = frame_shape[:2]

            nose_tip = landmarks_68[30]
            chin = landmarks_68[8]
            left_eye_corner = landmarks_68[36]
            right_eye_corner = landmarks_68[45]
            left_mouth = landmarks_68[48]
            right_mouth = landmarks_68[54]

            image_points = np.array([
                nose_tip, chin, left_eye_corner,
                right_eye_corner, left_mouth, right_mouth,
            ], dtype=np.float64)

            focal_length = w
            camera_matrix = np.array([
                [focal_length, 0, w / 2],
                [0, focal_length, h / 2],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            success, rvec, tvec = cv2.solvePnP(
                _DLIB_3D_MODEL_POINTS, image_points,
                camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return default_result

            rmat, _ = cv2.Rodrigues(rvec)
            sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
            singular = sy < 1e-6

            if not singular:
                pitch = np.degrees(np.arctan2(rmat[2, 1], rmat[2, 2]))
                yaw = np.degrees(np.arctan2(-rmat[2, 0], sy))
                roll = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
            else:
                pitch = np.degrees(np.arctan2(-rmat[1, 2], rmat[1, 1]))
                yaw = np.degrees(np.arctan2(-rmat[2, 0], sy))
                roll = 0.0

            return {
                "pitch": round(float(pitch), 1),
                "yaw": round(float(yaw), 1),
                "roll": round(float(roll), 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"dlib头部姿态估计失败: {e}")
            return default_result

    @staticmethod
    def _estimate_body_pose_heuristic(face_rect: tuple, frame_shape: tuple) -> dict:
        """基于人脸位置和大小的简单身体姿态启发式估计

        根据人脸在画面中的位置和大小推断身体姿态：
        - 人脸偏下且较大 → 前倾
        - 人脸偏下且非常大 → 趴桌
        - 人脸正常位置 → 正常
        - 无人脸 → 离座（由上层处理）
        """
        default_result = {"label": "正常", "score": 100,
                          "shoulder_tilt": 0.0, "spine_angle": 0.0, "available": False}
        try:
            if face_rect is None:
                return default_result

            h, w = frame_shape[:2]
            fx, fy, fw, fh = face_rect

            face_center_y = (fy + fh / 2) / h
            face_height_ratio = fh / h
            face_center_x = (fx + fw / 2) / w

            if face_center_y > 0.8 and face_height_ratio > 0.45:
                label, score = "趴桌", 10
            elif face_center_y > 0.7 and face_height_ratio > 0.35:
                label, score = "前倾", 70
            elif abs(face_center_x - 0.5) > 0.3:
                label, score = "前倾", 70
            else:
                label, score = "正常", 100

            return {
                "label": label,
                "score": score,
                "shoulder_tilt": 0.0,
                "spine_angle": 0.0,
                "available": True,
            }
        except Exception as e:
            logger.debug(f"身体姿态启发式估计失败: {e}")
            return default_result

    @staticmethod
    def _score_to_color(score: float) -> str:
        """专注度分数转颜色"""
        if score >= 65:
            return "#67C23A"
        elif score >= 45:
            return "#E6A23C"
        elif score >= 25:
            return "#FF9D4D"
        else:
            return "#F56C6C"

    def release(self):
        """释放资源"""
        if self.pose_estimator:
            self.pose_estimator.close()
        logger.info("视觉模块资源已释放")
