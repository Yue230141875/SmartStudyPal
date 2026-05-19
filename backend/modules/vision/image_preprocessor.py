import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器：CLAHE增强 + Gamma校正 + 降噪 + Resize"""

    def __init__(self, clip_limit=2.0, tile_grid_size=(8, 8), max_width=640):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self.max_width = max_width
        logger.info(f"图像预处理器初始化: clip_limit={clip_limit}, max_width={max_width}")

    def apply_clahe(self, frame: np.ndarray) -> np.ndarray:
        """应用CLAHE自适应直方图均衡化，增强低光照图像"""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def apply_gamma(self, frame: np.ndarray, gamma: float = None) -> np.ndarray:
        """应用Gamma校正，自动根据亮度调整gamma值"""
        if gamma is None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            if mean_brightness < 80:
                gamma = 0.7
            elif mean_brightness > 200:
                gamma = 1.2
            else:
                gamma = 1.0
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(frame, table)

    def apply_denoise(self, frame: np.ndarray) -> np.ndarray:
        """应用高斯降噪"""
        return cv2.GaussianBlur(frame, (3, 3), 0)

    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """按比例缩放图像，最大宽度不超过max_width"""
        h, w = frame.shape[:2]
        if w > self.max_width:
            ratio = self.max_width / w
            new_w = self.max_width
            new_h = int(h * ratio)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def get_brightness(self, frame: np.ndarray) -> float:
        """获取图像平均亮度"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """完整预处理流水线：缩放→CLAHE→Gamma→降噪"""
        frame = self.resize_frame(frame)
        frame = self.apply_clahe(frame)
        frame = self.apply_gamma(frame)
        frame = self.apply_denoise(frame)
        return frame


def test():
    """图像预处理模块测试"""
    print("=== 图像预处理模块测试 ===")
    preprocessor = ImagePreprocessor()

    test_dir = Path(__file__).parent.parent.parent
    test_image_path = test_dir / "test_image.jpg"

    if not test_image_path.exists():
        fake_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = preprocessor.preprocess(fake_frame)
        brightness = preprocessor.get_brightness(result)
        print(f"[OK] 模拟图像预处理完成，输出尺寸: {result.shape}, 亮度: {brightness:.1f}")
        return

    frame = cv2.imread(str(test_image_path))
    if frame is None:
        print("[ERROR] 无法读取测试图片")
        return

    original_brightness = preprocessor.get_brightness(frame)
    result = preprocessor.preprocess(frame)
    processed_brightness = preprocessor.get_brightness(result)

    output_path = test_dir / "output_preprocessed.jpg"
    cv2.imwrite(str(output_path), result)
    print(f"[OK] 图像预处理完成")
    print(f"  原始尺寸: {frame.shape}, 亮度: {original_brightness:.1f}")
    print(f"  处理后尺寸: {result.shape}, 亮度: {processed_brightness:.1f}")
    print(f"  保存到: {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
