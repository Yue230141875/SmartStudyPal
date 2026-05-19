import logging
import numpy as np
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "shape_predictor_68_face_landmarks.dat"

try:
    import dlib
    _DLIB_AVAILABLE = True
except ImportError:
    _DLIB_AVAILABLE = False
    logger.warning("dlib 未安装，人脸检测功能不可用。请执行: pip install dlib")


class FaceDetector:
    """Dlib 68点人脸检测器，支持主脸选择和EAR计算"""

    def __init__(self, model_path: str = None, upsample_times: int = 1):
        if not _DLIB_AVAILABLE:
            raise RuntimeError("dlib 未安装，人脸检测功能不可用")
        path = Path(model_path) if model_path else MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Dlib模型文件未找到: {path}\n"
                "请下载 shape_predictor_68_face_landmarks.dat 放到 backend/models/ 目录\n"
                "下载地址: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(str(path))
        self.upsample_times = upsample_times
        logger.info(f"人脸检测器初始化完成，模型路径: {path}")

    def detect(self, frame: np.ndarray) -> dict:
        """检测人脸并返回68个关键点

        返回:
            dict: {
                "face_detected": bool,
                "landmarks_68": np.ndarray (68,2) 或 None,
                "face_rect": tuple (x,y,w,h) 或 None,
                "num_faces": int
            }
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = self.detector(gray, self.upsample_times)

        if len(rects) == 0:
            return {
                "face_detected": False,
                "landmarks_68": None,
                "face_rect": None,
                "num_faces": 0
            }

        main_rect = self._select_main_face(rects)
        shape = self.predictor(gray, main_rect)
        landmarks = np.array([[p.x, p.y] for p in shape.parts()])

        return {
            "face_detected": True,
            "landmarks_68": landmarks,
            "face_rect": (main_rect.left(), main_rect.top(),
                          main_rect.width(), main_rect.height()),
            "num_faces": len(rects)
        }

    def _select_main_face(self, rects) -> "dlib.rectangle":
        """选择主脸（面积最大的脸）"""
        if len(rects) == 1:
            return rects[0]
        best_rect = rects[0]
        best_area = rects[0].width() * rects[0].height()
        for rect in rects[1:]:
            area = rect.width() * rect.height()
            if area > best_area:
                best_area = area
                best_rect = rect
        return best_rect

    def get_eye_points(self, landmarks: np.ndarray) -> tuple:
        """提取左右眼关键点

        左眼: landmarks[36:42], 右眼: landmarks[42:48]
        """
        left_eye = landmarks[36:42]
        right_eye = landmarks[42:48]
        return left_eye, right_eye

    def calculate_ear(self, eye_points: np.ndarray) -> float:
        """计算单眼的Eye Aspect Ratio (EAR)

        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        from scipy.spatial.distance import euclidean
        vertical_1 = euclidean(eye_points[1], eye_points[5])
        vertical_2 = euclidean(eye_points[2], eye_points[4])
        horizontal = euclidean(eye_points[0], eye_points[3])
        if horizontal == 0:
            return 0.0
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear

    def detect_blink(self, ear_left: float, ear_right: float,
                     ear_threshold: float = 0.21) -> bool:
        """检测是否眨眼（EAR低于阈值）"""
        avg_ear = (ear_left + ear_right) / 2.0
        return avg_ear < ear_threshold


def test():
    """人脸检测模块测试"""
    print("=== 人脸检测模块测试 ===")
    if not _DLIB_AVAILABLE:
        print("[SKIP] dlib 未安装，跳过人脸检测测试")
        return
    if not MODEL_PATH.exists():
        print(f"[SKIP] Dlib模型文件不存在: {MODEL_PATH}")
        return

    detector = FaceDetector()
    fake_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result = detector.detect(fake_frame)
    print(f"[OK] 人脸检测模块初始化成功")
    print(f"  模拟帧检测结果: face_detected={result['face_detected']}, num_faces={result['num_faces']}")

    test_dir = Path(__file__).parent.parent.parent
    test_image_path = test_dir / "test_image.jpg"
    if test_image_path.exists():
        frame = cv2.imread(str(test_image_path))
        if frame is not None:
            result = detector.detect(frame)
            if result["face_detected"]:
                left_eye, right_eye = detector.get_eye_points(result["landmarks_68"])
                ear_left = detector.calculate_ear(left_eye)
                ear_right = detector.calculate_ear(right_eye)
                print(f"  真实图像检测: face_detected=True, EAR左={ear_left:.3f}, EAR右={ear_right:.3f}")
            else:
                print(f"  真实图像检测: 未检测到人脸")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
