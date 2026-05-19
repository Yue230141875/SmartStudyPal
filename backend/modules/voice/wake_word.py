import logging

logger = logging.getLogger(__name__)

WAKE_WORDS = ["阿米娅", "amiya", "你好", "小雅", "开始计时", "暂停", "继续"]


class WakeWordDetector:
    """唤醒词检测器，支持文本级和音频级检测"""

    def __init__(self, wake_words: list = None):
        self.wake_words = wake_words or WAKE_WORDS
        logger.info(f"唤醒词检测器初始化: {self.wake_words}")

    def detect(self, text: str) -> dict:
        """检测文本中是否包含唤醒词

        返回:
            {"detected": bool, "keyword": str or None, "position": int}
        """
        if not text:
            return {"detected": False, "keyword": None, "position": -1}

        text_lower = text.lower().strip()
        for word in self.wake_words:
            pos = text_lower.find(word.lower())
            if pos >= 0:
                logger.debug(f"检测到唤醒词: '{word}' (位置: {pos})")
                return {"detected": True, "keyword": word, "position": pos}

        return {"detected": False, "keyword": None, "position": -1}

    def detect_from_audio(self, audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """从音频数据检测唤醒词（需要配合ASR使用）

        参数:
            audio_bytes: 原始PCM音频数据
            sample_rate: 采样率

        返回:
            {"detected": bool, "keyword": str or None, "text": str}
        """
        try:
            from .vad_detector import VADDetector, _VAD_AVAILABLE
            if not _VAD_AVAILABLE:
                return {"detected": False, "keyword": None, "text": ""}

            vad = VADDetector()
            speech_ratio = vad.process_audio(audio_bytes)
            if speech_ratio < 0.1:
                return {"detected": False, "keyword": None, "text": ""}

            return {"detected": False, "keyword": None, "text": "[需要ASR配合]"}
        except Exception as e:
            logger.debug(f"音频唤醒词检测失败: {e}")
            return {"detected": False, "keyword": None, "text": ""}

    def add_wake_word(self, word: str):
        """添加唤醒词"""
        if word and word not in self.wake_words:
            self.wake_words.append(word)
            logger.info(f"添加唤醒词: '{word}'")

    def remove_wake_word(self, word: str):
        """移除唤醒词"""
        if word in self.wake_words:
            self.wake_words.remove(word)
            logger.info(f"移除唤醒词: '{word}'")


def detect(text: str) -> bool:
    """便捷函数：检测文本中是否包含唤醒词"""
    detector = WakeWordDetector()
    result = detector.detect(text)
    return result["detected"]


def test():
    """唤醒词检测模块测试"""
    print("=== 唤醒词检测模块测试 ===")
    detector = WakeWordDetector()

    test_cases = [
        ("阿米娅，开始计时", True),
        ("amiya暂停", True),
        ("你好，切换白噪音", True),
        ("今天天气不错", False),
        ("开始计时", True),
        ("小雅，帮我计时", True),
        ("继续学习", True),
        ("我正在看书", False),
    ]

    all_pass = True
    for text, expected in test_cases:
        result = detector.detect(text)
        status = "OK" if result["detected"] == expected else "FAIL"
        if result["detected"] != expected:
            all_pass = False
        print(f"  [{status}] '{text}' -> detected={result['detected']}, "
              f"keyword='{result['keyword']}' (期望: {expected})")

    if all_pass:
        print("[OK] 唤醒词检测测试全部通过")
    else:
        print("[FAIL] 部分唤醒词检测测试未通过")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
