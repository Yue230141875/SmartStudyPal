import logging

logger = logging.getLogger(__name__)

try:
    from .asr_whisper import ASRWhisper, _WHISPER_AVAILABLE
    from .vad_detector import VADDetector, _VAD_AVAILABLE
    from .emotion_classifier import EmotionClassifier, _LIBROSA_AVAILABLE
    from .tts_engine import TTSEngine, _TTS_AVAILABLE
    from .wake_word import WakeWordDetector, detect
    from .amiya_tts import AmiyaTTS
    _AMIYA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"语音模块导入失败: {e}")
    _AMIYA_AVAILABLE = False


class VoiceManager:
    """语音模块统一管理器"""

    def __init__(self):
        self.asr = None
        self.vad = None
        self.emotion_classifier = None
        self.tts = None
        self.amiya_tts = None
        self.wake_word_detector = WakeWordDetector()
        self._voice_available = False

        try:
            if _WHISPER_AVAILABLE:
                self.asr = ASRWhisper()
        except Exception as e:
            logger.warning(f"ASR初始化失败: {e}")

        try:
            if _VAD_AVAILABLE:
                self.vad = VADDetector()
        except Exception as e:
            logger.warning(f"VAD初始化失败: {e}")

        try:
            if _LIBROSA_AVAILABLE:
                self.emotion_classifier = EmotionClassifier()
        except Exception as e:
            logger.warning(f"情绪分类器初始化失败: {e}")

        try:
            if _TTS_AVAILABLE:
                self.tts = TTSEngine()
        except Exception as e:
            logger.warning(f"TTS引擎初始化失败: {e}")

        try:
            if _AMIYA_AVAILABLE:
                self.amiya_tts = AmiyaTTS()
                logger.info("AmiyaTTS 初始化成功")
                self._pre_synthesize_amiya()
        except Exception as e:
            logger.warning(f"阿米娅TTS初始化失败: {e}")

        self._voice_available = (self.asr is not None or self.vad is not None or self.amiya_tts is not None)
        if self._voice_available:
            logger.info("语音模块初始化完成")
        else:
            logger.warning("语音模块不可用")

    def _pre_synthesize_amiya(self):
        """预合成阿米娅常用语音（后台线程，不阻塞启动）"""
        if not self.amiya_tts:
            return
        import threading
        def _run():
            try:
                results = self.amiya_tts.pre_synthesize()
                if results:
                    logger.info(f"预合成完成，共 {len(results)} 条语音")
            except Exception as e:
                logger.warning(f"预合成失败: {e}")
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        logger.info("预合成任务已在后台启动")

    def process_audio(self, audio_bytes: bytes, sample_rate: int = 16000,
                       language: str = "zh") -> dict:
        """处理音频数据，返回综合结果"""
        result = {
            "text": "",
            "confidence": 0.0,
            "emotion": {"label": "未知", "score": 50},
            "wake_word": {"detected": False, "keyword": None},
            "speech_ratio": 0.0,
        }

        if self.vad:
            result["speech_ratio"] = self.vad.process_audio(audio_bytes)

        if self.asr and result["speech_ratio"] > 0.1:
            asr_result = self.asr.transcribe_audio_bytes(audio_bytes, sample_rate, language)
            result["text"] = asr_result.get("text", "")
            result["confidence"] = asr_result.get("confidence", 0.0)

            if result["text"]:
                wake_result = self.wake_word_detector.detect(result["text"])
                result["wake_word"] = wake_result

        if self.emotion_classifier:
            try:
                import numpy as np
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                if len(audio_np) > sample_rate * 0.5:
                    emotion_result = self.emotion_classifier.classify(audio_np)
                    result["emotion"] = {
                        "label": emotion_result["label"],
                        "score": emotion_result["score"],
                        "confidence": emotion_result.get("confidence", 0.0),
                    }
            except Exception as e:
                logger.debug(f"情绪分类失败: {e}")

        return result

    def text_to_speech(self, text: str, output_path: str = None) -> dict:
        """文字转语音"""
        if not self.tts:
            return {"success": False, "message": "TTS引擎不可用"}

        try:
            if output_path:
                self.tts.save_to_file(text, output_path)
                return {"success": True, "file_path": output_path}
            else:
                self.tts.speak(text)
                return {"success": True, "message": "语音播放完成"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def amiya_speak(self, text: str = None, force_synthesize: bool = False) -> dict:
        """
        阿米娅语音合成
        
        Args:
            text: 要合成的文本，默认为 "博士，我在"
            force_synthesize: 是否强制使用TTS合成（跳过预设语音匹配）
        
        Returns:
            dict: 合成结果
        """
        if not self.amiya_tts:
            return {"success": False, "message": "阿米娅TTS不可用"}

        try:
            if text:
                return self.amiya_tts.synthesize(text, force_synthesize=force_synthesize)
            else:
                return self.amiya_tts.synthesize("博士，我在", force_synthesize=force_synthesize)
        except Exception as e:
            logger.error(f"阿米娅语音合成失败: {e}")
            return {"success": False, "message": str(e)}

    def get_amiya_voices(self) -> list:
        """获取阿米娅可用语音列表"""
        if not self.amiya_tts:
            return []
        return self.amiya_tts.get_available_voices()

    def release(self):
        """释放资源"""
        logger.info("语音模块资源已释放")
