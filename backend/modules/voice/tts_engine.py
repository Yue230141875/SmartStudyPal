import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    logger.warning("pyttsx3 未安装，语音合成功能不可用。请执行: pip install pyttsx3")


class TTSEngine:
    """pyttsx3语音合成引擎，支持语速/音量调节和语音列表"""

    def __init__(self, rate: int = 180, volume: float = 0.9):
        if not _TTS_AVAILABLE:
            raise RuntimeError("pyttsx3 未安装，语音合成功能不可用")
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        self._rate = rate
        self._volume = volume
        self._check_chinese_voice()
        logger.info(f"TTS引擎初始化: rate={rate}, volume={volume}")

    def _check_chinese_voice(self):
        """检查并设置中文语音"""
        voices = self.engine.getProperty("voices")
        chinese_voice = None
        for voice in voices:
            name_lower = voice.name.lower()
            id_lower = voice.id.lower()
            if any(kw in name_lower or kw in id_lower for kw in
                   ["chinese", "zh", "huihui", "yaoyao", "kangkang", "lili"]):
                chinese_voice = voice
                break
        if chinese_voice:
            self.engine.setProperty("voice", chinese_voice.id)
            logger.info(f"已设置中文语音: {chinese_voice.name}")
        else:
            logger.warning("未检测到中文语音包，请在Windows设置中下载中文语音")

    def speak(self, text: str):
        """直接朗读文本"""
        self.engine.say(text)
        self.engine.runAndWait()

    def save_to_file(self, text: str, filename: str):
        """保存语音到文件"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine.save_to_file(text, str(output_path))
        self.engine.runAndWait()
        logger.info(f"语音已保存到: {output_path}")

    def set_rate(self, rate: int):
        """设置语速"""
        self._rate = rate
        self.engine.setProperty("rate", rate)

    def set_volume(self, volume: float):
        """设置音量 (0.0-1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        self.engine.setProperty("volume", self._volume)

    def get_voices(self) -> list:
        """获取可用语音列表"""
        voices = self.engine.getProperty("voices")
        result = []
        for v in voices:
            result.append({
                "id": v.id,
                "name": v.name,
                "languages": v.languages if hasattr(v, "languages") else [],
            })
        return result

    def get_current_config(self) -> dict:
        """获取当前配置"""
        return {
            "rate": self._rate,
            "volume": self._volume,
            "voices_count": len(self.engine.getProperty("voices")),
        }


def test():
    """TTS引擎测试"""
    print("=== TTS引擎测试 ===")
    if not _TTS_AVAILABLE:
        print("[SKIP] pyttsx3 未安装，跳过TTS测试")
        return

    try:
        tts = TTSEngine()
        config = tts.get_current_config()
        print(f"[OK] TTS引擎初始化成功: {config}")

        voices = tts.get_voices()
        print(f"  可用语音数量: {len(voices)}")
        for v in voices[:3]:
            print(f"    - {v['name']}")

        print("[INFO] 正在合成语音: 你好，我是你的智能学习助手")
        tts.speak("你好，我是你的智能学习助手")
        print("[OK] TTS语音合成测试完成")
    except Exception as e:
        print(f"[ERROR] TTS测试失败: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
