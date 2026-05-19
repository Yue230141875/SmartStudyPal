import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False
    logger.warning("mediapipe 未安装，姿态估计功能不可用。请执行: pip install mediapipe")

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
POSE_MODEL_PATH = MODELS_DIR / "pose_landmarker.task"
FACE_LANDMARKER_MODEL_PATH = MODELS_DIR / "face_landmarker.task"


class PoseEstimator:
    """姿态估计器：使用 MediaPipe Tasks API (0.10.x+)"""

    def __init__(self, min_face_confidence: float = 0.5,
                 min_pose_confidence: float = 0.5,
                 static_image_mode: bool = False):
        if not _MP_AVAILABLE:
            raise RuntimeError("mediapipe 未安装，姿态估计功能不可用")

        self._pose_landmarker = None
        self._face_landmarker = None
        self._use_tasks_api = hasattr(mp, 'tasks')

        if self._use_tasks_api:
            self._init_tasks_api(min_face_confidence, min_pose_confidence)
        else:
            self._init_legacy_api(min_face_confidence, min_pose_confidence)

        self._3d_model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0),
        ], dtype=np.float64)

        logger.info("姿态估计器初始化完成")

    def _init_tasks_api(self, min_face_confidence: float, min_pose_confidence: float):
        """初始化 MediaPipe Tasks API (0.10.x+)"""
        try:
            if POSE_MODEL_PATH.exists():
                options = mp.tasks.vision.PoseLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    min_pose_detection_confidence=min_pose_confidence,
                    min_pose_presence_confidence=min_pose_confidence,
                )
                self._pose_landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
                logger.info(f"PoseLandmarker (Tasks API) 初始化成功")
            else:
                logger.warning(f"Pose模型文件不存在: {POSE_MODEL_PATH}，身体姿态检测不可用")
        except Exception as e:
            logger.warning(f"PoseLandmarker (Tasks API) 初始化失败: {e}")

        try:
            if FACE_LANDMARKER_MODEL_PATH.exists():
                options = mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(FACE_LANDMARKER_MODEL_PATH)),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    min_face_detection_confidence=min_face_confidence,
                    min_face_presence_confidence=min_face_confidence,
                    num_faces=1,
                )
                self._face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
                logger.info(f"FaceLandmarker (Tasks API) 初始化成功")
            else:
                logger.warning(f"FaceLandmarker模型文件不存在: {FACE_LANDMARKER_MODEL_PATH}，头部姿态使用dlib备用方案")
        except Exception as e:
            logger.warning(f"FaceLandmarker (Tasks API) 初始化失败: {e}，头部姿态使用dlib备用方案")

    def _init_legacy_api(self, min_face_confidence: float, min_pose_confidence: float):
        """初始化旧版 MediaPipe Solutions API (0.10.x 之前)"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose

        self._face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_face_confidence,
            min_tracking_confidence=min_face_confidence,
            static_image_mode=True,
        )

        self._pose = self.mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=min_pose_confidence,
            min_tracking_confidence=min_pose_confidence,
            static_image_mode=True,
        )

        self._face_mesh_indices = [1, 152, 33, 263, 61, 291]
        logger.info("姿态估计器 (Legacy API) 初始化完成")

    def process_frame(self, frame: np.ndarray) -> dict:
        """处理单帧，返回头部和身体姿态数据"""
        if self._use_tasks_api:
            return self._process_tasks_api(frame)
        else:
            return self._process_legacy_api(frame)

    def _process_tasks_api(self, frame: np.ndarray) -> dict:
        """使用 Tasks API 处理帧"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        head_result = self._estimate_head_pose_tasks(mp_image, rgb.shape[:2])
        body_result = self._estimate_body_pose_tasks(mp_image)

        return {"head": head_result, "body": body_result}

    def _estimate_head_pose_tasks(self, mp_image, shape) -> dict:
        """使用 FaceLandmarker Tasks API 估计头部姿态"""
        default_result = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "available": False}

        if self._face_landmarker is None:
            return default_result

        try:
            result = self._face_landmarker.detect(mp_image)
            if not result.face_landmarks:
                return default_result

            landmarks = result.face_landmarks[0]
            h, w = shape

            face_mesh_indices = [1, 152, 33, 263, 61, 291]
            image_points = np.array([
                [landmarks[idx].x * w, landmarks[idx].y * h]
                for idx in face_mesh_indices
            ], dtype=np.float64)

            focal_length = w
            camera_matrix = np.array([
                [focal_length, 0, w / 2],
                [0, focal_length, h / 2],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            success, rvec, tvec = cv2.solvePnP(
                self._3d_model_points, image_points,
                camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return default_result

            rmat, _ = cv2.Rodrigues(rvec)
            angles = self._rotation_matrix_to_euler_angles(rmat)

            return {
                "pitch": round(float(angles[0]), 1),
                "yaw": round(float(angles[1]), 1),
                "roll": round(float(angles[2]), 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"头部姿态估计失败 (Tasks API): {e}")
            return default_result

    def _estimate_body_pose_tasks(self, mp_image) -> dict:
        """使用 PoseLandmarker Tasks API 估计身体姿态"""
        default_result = {"label": "离座", "score": 0, "shoulder_tilt": 0.0,
                          "spine_angle": 0.0, "available": False}

        if self._pose_landmarker is None:
            return default_result

        try:
            result = self._pose_landmarker.detect(mp_image)
            if not result.pose_landmarks:
                return default_result

            landmarks = result.pose_landmarks[0]

            nose = landmarks[0]
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_hip = landmarks[23]
            right_hip = landmarks[24]

            shoulder_avg_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_avg_y = (left_hip.y + right_hip.y) / 2
            shoulder_width = abs(left_shoulder.x - right_shoulder.x)

            if hip_avg_y < 0.1 and shoulder_avg_y < 0.1:
                return default_result

            shoulder_tilt = abs(left_shoulder.y - right_shoulder.y) / max(shoulder_width, 0.01)
            shoulder_tilt_deg = shoulder_tilt * 90

            spine_dx = 0.5 - (left_shoulder.x + right_shoulder.x) / 2
            spine_dy = hip_avg_y - shoulder_avg_y
            spine_angle = 0.0
            if spine_dy > 0.01:
                spine_angle = abs(np.degrees(np.arctan2(spine_dx, spine_dy)))

            head_shoulder_ratio = (shoulder_avg_y - nose.y) / max(shoulder_width, 0.01)

            if head_shoulder_ratio < 0.3:
                label, score = "趴桌", 10
            elif head_shoulder_ratio < 0.5:
                label, score = "前倾", 50
            elif head_shoulder_ratio < 1.0:
                label, score = "正常", 100
            else:
                label, score = "正常", 100

            if shoulder_tilt_deg > 15:
                label = "前倾"
                score = min(score, 50)

            return {
                "label": label,
                "score": score,
                "shoulder_tilt": round(shoulder_tilt_deg, 1),
                "spine_angle": round(spine_angle, 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"身体姿态估计失败 (Tasks API): {e}")
            return default_result

    def _process_legacy_api(self, frame: np.ndarray) -> dict:
        """使用旧版 Solutions API 处理帧"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False

        head_result = self._estimate_head_pose_legacy(rgb)
        body_result = self._estimate_body_pose_legacy(rgb)

        return {"head": head_result, "body": body_result}

    def _estimate_head_pose_legacy(self, rgb: np.ndarray) -> dict:
        """旧版 FaceMesh 头部姿态估计"""
        default_result = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "available": False}
        try:
            face_results = self._face_mesh.process(rgb)
            if not face_results.multi_face_landmarks:
                return default_result

            face_landmarks = face_results.multi_face_landmarks[0]
            h, w = rgb.shape[:2]

            image_points = np.array([
                [face_landmarks.landmark[idx].x * w,
                 face_landmarks.landmark[idx].y * h]
                for idx in self._face_mesh_indices
            ], dtype=np.float64)

            focal_length = w
            camera_matrix = np.array([
                [focal_length, 0, w / 2],
                [0, focal_length, h / 2],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            success, rvec, tvec = cv2.solvePnP(
                self._3d_model_points, image_points,
                camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return default_result

            rmat, _ = cv2.Rodrigues(rvec)
            angles = self._rotation_matrix_to_euler_angles(rmat)

            return {
                "pitch": round(float(angles[0]), 1),
                "yaw": round(float(angles[1]), 1),
                "roll": round(float(angles[2]), 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"头部姿态估计失败 (Legacy): {e}")
            return default_result

    def _estimate_body_pose_legacy(self, rgb: np.ndarray) -> dict:
        """旧版 Pose 身体姿态估计"""
        default_result = {"label": "离座", "score": 0, "shoulder_tilt": 0.0,
                          "spine_angle": 0.0, "available": False}
        try:
            pose_results = self._pose.process(rgb)
            if not pose_results.pose_landmarks:
                return default_result

            landmarks = pose_results.pose_landmarks.landmark
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]

            shoulder_avg_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_avg_y = (left_hip.y + right_hip.y) / 2
            shoulder_width = abs(left_shoulder.x - right_shoulder.x)

            if hip_avg_y < 0.1 and shoulder_avg_y < 0.1:
                return default_result

            shoulder_tilt = abs(left_shoulder.y - right_shoulder.y) / max(shoulder_width, 0.01)
            shoulder_tilt_deg = shoulder_tilt * 90

            spine_dx = 0.5 - (left_shoulder.x + right_shoulder.x) / 2
            spine_dy = hip_avg_y - shoulder_avg_y
            spine_angle = 0.0
            if spine_dy > 0.01:
                spine_angle = abs(np.degrees(np.arctan2(spine_dx, spine_dy)))

            head_shoulder_ratio = (shoulder_avg_y - nose.y) / max(shoulder_width, 0.01)

            if head_shoulder_ratio < 0.3:
                label, score = "趴桌", 10
            elif head_shoulder_ratio < 0.5:
                label, score = "前倾", 50
            elif head_shoulder_ratio < 1.0:
                label, score = "正常", 100
            else:
                label, score = "正常", 100

            if shoulder_tilt_deg > 15:
                label = "前倾"
                score = min(score, 50)

            return {
                "label": label,
                "score": score,
                "shoulder_tilt": round(shoulder_tilt_deg, 1),
                "spine_angle": round(spine_angle, 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"身体姿态估计失败 (Legacy): {e}")
            return default_result

    def estimate_head_pose_from_dlib(self, landmarks_68: np.ndarray, frame_shape: tuple) -> dict:
        """使用 dlib 68点关键点估计头部姿态（备用方案）

        参数:
            landmarks_68: dlib 68点关键点 (68, 2)
            frame_shape: (h, w, c) 帧形状
        """
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
                nose_tip,
                chin,
                left_eye_corner,
                right_eye_corner,
                left_mouth,
                right_mouth,
            ], dtype=np.float64)

            focal_length = w
            camera_matrix = np.array([
                [focal_length, 0, w / 2],
                [0, focal_length, h / 2],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            success, rvec, tvec = cv2.solvePnP(
                self._3d_model_points, image_points,
                camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return default_result

            rmat, _ = cv2.Rodrigues(rvec)
            angles = self._rotation_matrix_to_euler_angles(rmat)

            return {
                "pitch": round(float(angles[0]), 1),
                "yaw": round(float(angles[1]), 1),
                "roll": round(float(angles[2]), 1),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"dlib头部姿态估计失败: {e}")
            return default_result

    def detect(self, frame: np.ndarray) -> dict:
        """兼容旧接口：返回身体姿态评分"""
        result = self.process_frame(frame)
        return {
            "score": result["body"]["score"],
            "label": result["body"]["label"],
        }

    @staticmethod
    def _rotation_matrix_to_euler_angles(rmat: np.ndarray) -> np.ndarray:
        """旋转矩阵转欧拉角 (pitch, yaw, roll)"""
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(rmat[2, 1], rmat[2, 2])
            yaw = np.arctan2(-rmat[2, 0], sy)
            roll = np.arctan2(rmat[1, 0], rmat[0, 0])
        else:
            pitch = np.arctan2(-rmat[1, 2], rmat[1, 1])
            yaw = np.arctan2(-rmat[2, 0], sy)
            roll = 0

        return np.degrees(np.array([pitch, yaw, roll]))

    def close(self):
        """释放资源"""
        if self._pose_landmarker is not None:
            self._pose_landmarker.close()
        if self._face_landmarker is not None:
            self._face_landmarker.close()
        if hasattr(self, '_face_mesh'):
            self._face_mesh.close()
        if hasattr(self, '_pose'):
            self._pose.close()
        logger.info("姿态估计器资源已释放")

    @property
    def head_pose_available(self):
        """头部姿态估计是否可用"""
        if self._use_tasks_api:
            return self._face_landmarker is not None
        return hasattr(self, '_face_mesh')

    @property
    def body_pose_available(self):
        """身体姿态估计是否可用"""
        if self._use_tasks_api:
            return self._pose_landmarker is not None
        return hasattr(self, '_pose')
