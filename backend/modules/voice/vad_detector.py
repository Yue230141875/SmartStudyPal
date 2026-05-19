import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import webrtcvad
    _VAD_AVAILABLE = True
except ImportError:
    _VAD_AVAILABLE = False
    logger.warning("webrtcvad 未安装，VAD功能不可用。请执行: pip install webrtcvad-wheels")


class VADDetector:
    """WebRTC VAD语音活动检测器，支持帧级检测和语音段提取"""

    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000,
                 frame_duration_ms: int = 30):
        if not _VAD_AVAILABLE:
            raise RuntimeError("webrtcvad 未安装，VAD功能不可用")
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.frame_bytes = self.frame_size * 2
        logger.info(f"VAD检测器初始化: aggressiveness={aggressiveness}, "
                     f"sample_rate={sample_rate}, frame_size={self.frame_size}")

    def is_speech(self, audio_bytes: bytes) -> bool:
        """检测单帧是否为语音"""
        try:
            return self.vad.is_speech(audio_bytes, self.sample_rate)
        except Exception:
            return False

    def process_audio(self, audio_data: bytes) -> float:
        """处理完整音频数据，返回语音帧比例"""
        speech_frames = 0
        total_frames = 0
        for i in range(0, len(audio_data) - self.frame_bytes, self.frame_bytes):
            frame = audio_data[i:i + self.frame_bytes]
            if self.is_speech(frame):
                speech_frames += 1
            total_frames += 1
        if total_frames == 0:
            return 0.0
        return speech_frames / total_frames

    def extract_speech_segments(self, audio_data: bytes,
                                 min_speech_frames: int = 5,
                                 min_silence_frames: int = 10) -> list:
        """提取语音段

        参数:
            audio_data: 原始PCM音频数据
            min_speech_frames: 最小语音帧数（短于此的段被忽略）
            min_silence_frames: 最小静音帧数（用于分割语音段）

        返回:
            [{"start_frame": int, "end_frame": int, "start_ms": int, "end_ms": int}]
        """
        frames = []
        for i in range(0, len(audio_data) - self.frame_bytes, self.frame_bytes):
            frame = audio_data[i:i + self.frame_bytes]
            frames.append(self.is_speech(frame))

        segments = []
        in_speech = False
        start = 0
        silence_count = 0

        for i, is_sp in enumerate(frames):
            if is_sp:
                if not in_speech:
                    in_speech = True
                    start = i
                silence_count = 0
            else:
                if in_speech:
                    silence_count += 1
                    if silence_count >= min_silence_frames:
                        end = i - silence_count
                        if end - start >= min_speech_frames:
                            segments.append({
                                "start_frame": start,
                                "end_frame": end,
                                "start_ms": start * self.frame_duration_ms,
                                "end_ms": end * self.frame_duration_ms,
                            })
                        in_speech = False
                        silence_count = 0

        if in_speech:
            end = len(frames)
            if end - start >= min_speech_frames:
                segments.append({
                    "start_frame": start,
                    "end_frame": end,
                    "start_ms": start * self.frame_duration_ms,
                    "end_ms": end * self.frame_duration_ms,
                })

        return segments

    def get_speech_audio(self, audio_data: bytes, segments: list) -> bytes:
        """从原始音频中提取语音段的音频数据"""
        result = b""
        for seg in segments:
            start_byte = seg["start_frame"] * self.frame_bytes
            end_byte = seg["end_frame"] * self.frame_bytes
            result += audio_data[start_byte:end_byte]
        return result


def test():
    """VAD检测模块测试"""
    print("=== VAD检测模块测试 ===")
    if not _VAD_AVAILABLE:
        print("[SKIP] webrtcvad 未安装，跳过VAD测试")
        return

    detector = VADDetector()
    print(f"[OK] VAD检测器初始化成功 (frame_size={detector.frame_size})")

    test_dir = Path(__file__).parent.parent.parent
    test_audio_path = test_dir / "test_audio.wav"
    if test_audio_path.exists():
        with open(str(test_audio_path), "rb") as f:
            f.read(44)
            audio_data = f.read()
        ratio = detector.process_audio(audio_data)
        segments = detector.extract_speech_segments(audio_data)
        print(f"  语音帧比例: {ratio:.2%}")
        print(f"  检测到 {len(segments)} 个语音段")
        for i, seg in enumerate(segments[:3]):
            print(f"    段{i+1}: {seg['start_ms']}ms - {seg['end_ms']}ms")
    else:
        print("[INFO] 测试音频不存在，跳过真实音频测试")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
