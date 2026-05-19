import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False
    logger.warning("librosa 未安装，情绪分类功能不可用。请执行: pip install librosa")


EMOTION_SCORE_MAP = {
    "专注": 90,
    "平静": 80,
    "烦躁": 30,
    "疲惫": 20,
    "焦虑": 25,
}


class EmotionClassifier:
    """语音情绪分类器，基于MFCC+ZCR+RMS特征"""

    def __init__(self, sample_rate: int = 16000):
        if not _LIBROSA_AVAILABLE:
            raise RuntimeError("librosa 未安装，情绪分类功能不可用")
        self.sample_rate = sample_rate
        logger.info(f"情绪分类器初始化: sample_rate={sample_rate}")

    def extract_features(self, audio_np: np.ndarray) -> dict:
        """提取音频特征

        返回:
            {"mfcc_mean": list, "zcr_mean": float, "rms_mean": float,
             "spectral_centroid_mean": float, "mfcc_delta_mean": list}
        """
        mfcc = librosa.feature.mfcc(y=audio_np, sr=self.sample_rate, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)

        zcr = librosa.feature.zero_crossing_rate(y=audio_np)
        zcr_mean = float(np.mean(zcr))

        rms = librosa.feature.rms(y=audio_np)
        rms_mean = float(np.mean(rms))

        spectral_centroid = librosa.feature.spectral_centroid(y=audio_np, sr=self.sample_rate)
        spectral_centroid_mean = float(np.mean(spectral_centroid))

        mfcc_delta = librosa.feature.delta(mfcc)
        mfcc_delta_mean = np.mean(mfcc_delta, axis=1)

        return {
            "mfcc_mean": mfcc_mean.tolist(),
            "zcr_mean": zcr_mean,
            "rms_mean": rms_mean,
            "spectral_centroid_mean": spectral_centroid_mean,
            "mfcc_delta_mean": mfcc_delta_mean.tolist(),
        }

    def classify(self, audio_np: np.ndarray) -> dict:
        """分类语音情绪

        返回:
            {"label": str, "score": float, "confidence": float, "features": dict}
        """
        features = self.extract_features(audio_np)

        zcr = features["zcr_mean"]
        rms = features["rms_mean"]
        sc = features["spectral_centroid_mean"]

        if zcr > 0.1 and rms > 0.02:
            label = "烦躁"
            confidence = min(1.0, (zcr - 0.1) * 5 + rms * 10)
        elif zcr < 0.05 and rms < 0.01:
            label = "疲惫"
            confidence = min(1.0, (0.05 - zcr) * 10 + (0.01 - rms) * 50)
        elif zcr < 0.03 and rms < 0.005:
            label = "平静"
            confidence = 0.6
        elif rms > 0.03 and sc > 3000:
            label = "焦虑"
            confidence = 0.5
        else:
            label = "专注"
            confidence = 0.7

        score = EMOTION_SCORE_MAP.get(label, 50)

        return {
            "label": label,
            "score": score,
            "confidence": round(confidence, 2),
            "features": features,
        }

    @staticmethod
    def emotion_to_score(emotion_label: str) -> int:
        """情绪标签转分数"""
        return EMOTION_SCORE_MAP.get(emotion_label, 50)


def test():
    """情绪分类模块测试"""
    print("=== 情绪分类模块测试 ===")
    if not _LIBROSA_AVAILABLE:
        print("[SKIP] librosa 未安装，跳过情绪分类测试")
        return

    classifier = EmotionClassifier()

    test_cases = [
        ("低能量（疲惫模拟）", np.random.randn(16000).astype(np.float32) * 0.001),
        ("中等能量（专注模拟）", np.random.randn(16000).astype(np.float32) * 0.01),
        ("高能量（烦躁模拟）", np.random.randn(16000).astype(np.float32) * 0.05),
    ]

    for name, audio in test_cases:
        result = classifier.classify(audio)
        print(f"  {name}: label={result['label']}, score={result['score']}, "
              f"confidence={result['confidence']}")

    print("[OK] 情绪分类模块测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
