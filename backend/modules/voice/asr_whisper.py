import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import whisper
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    logger.warning("whisper 未安装，语音识别功能不可用。请执行: pip install openai-whisper")


class ASRWhisper:
    """Whisper语音识别引擎，支持多语言和置信度评分"""

    def __init__(self, model_name: str = "tiny"):
        if not _WHISPER_AVAILABLE:
            raise RuntimeError("whisper 未安装，语音识别功能不可用")
        try:
            self.model = whisper.load_model(model_name)
            self.model_name = model_name
            logger.info(f"Whisper {model_name} 模型加载成功")
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {e}")
            raise

    def transcribe(self, audio_path: str, language: str = "zh") -> dict:
        """语音识别

        参数:
            audio_path: 音频文件路径
            language: 语言代码 (zh/en/ja等)

        返回:
            {"text": str, "confidence": float, "language": str, "duration": float}
        """
        try:
            result = self.model.transcribe(audio_path, language=language)
            text = result.get("text", "").strip()
            segments = result.get("segments", [])

            confidence = 0.0
            duration = 0.0
            if segments:
                avg_logprob = sum(s.get("avg_logprob", 0) for s in segments) / len(segments)
                confidence = max(0, min(1, (avg_logprob + 1) / 1))
                duration = segments[-1].get("end", 0) - segments[0].get("start", 0)

            return {
                "text": text,
                "confidence": round(confidence, 3),
                "language": result.get("language", language),
                "duration": round(duration, 2),
            }
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return {"text": "", "confidence": 0.0, "language": language, "duration": 0.0, "error": str(e)}

    def transcribe_audio_bytes(self, audio_bytes: bytes, sample_rate: int = 16000,
                                language: str = "zh") -> dict:
        """从音频字节流进行识别

        参数:
            audio_bytes: 原始音频字节数据
            sample_rate: 采样率
            language: 语言代码

        返回:
            同 transcribe
        """
        tmp_path = None
        try:
            import numpy as np
            import struct

            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            if len(audio_np) < sample_rate:
                logger.debug(f"音频过短 ({len(audio_np)/sample_rate:.1f}s)，跳过识别")
                return {"text": "", "confidence": 0.0, "language": language, "duration": 0.0}

            tmp_dir = Path(tempfile.gettempdir()) / "smartstudypal"
            tmp_dir.mkdir(exist_ok=True)
            tmp_path = str(tmp_dir / f"asr_input_{os.getpid()}.wav")

            import scipy.io.wavfile as wavfile
            wavfile.write(tmp_path, sample_rate, audio_np)

            return self.transcribe(tmp_path, language=language)
        except Exception as e:
            logger.error(f"音频字节流识别失败: {e}")
            return {"text": "", "confidence": 0.0, "language": language, "duration": 0.0, "error": str(e)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def test():
    """语音识别模块测试"""
    print("=== 语音识别模块测试 ===")
    if not _WHISPER_AVAILABLE:
        print("[SKIP] whisper 未安装，跳过语音识别测试")
        return

    asr = ASRWhisper()
    print(f"[OK] Whisper {asr.model_name} 模型加载成功")

    test_dir = Path(__file__).parent.parent.parent
    test_audio_path = test_dir / "test_audio.wav"
    if test_audio_path.exists():
        result = asr.transcribe(str(test_audio_path))
        print(f"  识别结果: text='{result['text']}', confidence={result['confidence']}")
    else:
        print("[INFO] 测试音频 test_audio.wav 不存在，跳过真实音频测试")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
