import logging
import hashlib
import base64
import os
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    logger.warning("openai SDK 未安装，MiMo VoiceClone 不可用")

try:
    import soundfile as sf
    _SOUNDFILE_AVAILABLE = True
except ImportError:
    _SOUNDFILE_AVAILABLE = False


class AmiyaTTS:
    """
    阿米娅语音合成模块 - 基于 MiMo V2.5 VoiceClone
    
    使用阿米娅预录制语音作为参考样本，克隆音色后合成新语音。
    采用预合成模式：启动时生成常用语音文件，交互时直接播放缓存。
    """

    MIMO_API_KEY = "sk-cvnq5gxu7iehtpqymqteathbemx4rqh2asfli0lvkhdxmm0j"
    MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
    MIMO_MODEL = "mimo-v2.5-tts-voiceclone"

    REFERENCE_VOICE = "Reference.wav"

    PRESET_TEXTS = {
        "博士，我在": None,
        "博士，你好": None,
        "欢迎回来，博士": None,
        "怎么了，博士": None,
        "好的": None,
        "博士，一起加油吧": None,
        "博士，今天也要全力以赴哦": None,
        "我相信博士一定能做到的": None,
        "博士，专注当下，不要分心": None,
        "每一次努力都不会白费的，博士": None,
        "博士，休息好了再继续吧": None,
        "博士，有什么需要我帮忙的吗": None,
        "博士，我一直在这里等你": None,
        "博士，今天也请多关照了": None,
        "博士，集中注意力哦": None,
        "不要走神啦，博士": None,
        "博士，学习时间要好好利用哦": None,
        "博士，调整一下状态吧": None,
        "博士，深呼吸，重新专注起来": None,
    }

    ENCOURAGEMENT_TEXTS = [
        "博士，一起加油吧",
        "博士，今天也要全力以赴哦",
        "我相信博士一定能做到的",
        "博士，专注当下，不要分心",
        "每一次努力都不会白费的，博士",
        "博士，休息好了再继续吧",
    ]

    GREETING_TEXTS = [
        "博士，我在",
        "博士，你好",
        "欢迎回来，博士",
        "博士，有什么需要我帮忙的吗",
        "博士，我一直在这里等你",
        "博士，今天也请多关照了",
    ]

    FOCUS_REMINDER_TEXTS = [
        "博士，专注当下，不要分心",
        "博士，集中注意力哦",
        "不要走神啦，博士",
        "博士，学习时间要好好利用哦",
        "博士，调整一下状态吧",
        "博士，深呼吸，重新专注起来",
    ]

    AMIYA_STYLE = """
角色：明日方舟阿米娅，罗德岛的公开领袖，温柔而坚定的少女。
说话风格：温柔亲切但带着责任感，声音清亮干净，音调自然偏高，语速适中偏快，干脆利落不拖沓。
情绪基调：温暖、关怀，偶尔透露出与年龄不符的成熟与担当。
禁止：颤抖、沙哑、拖音、过度撒娇。
"""

    def __init__(self, voice_dir: str = None):
        if voice_dir is None:
            project_amiya = Path("d:/Vibe_Coidng/StudyRoom/amiya_voice")
            if project_amiya.exists():
                voice_dir = project_amiya
            else:
                base_dir = Path(__file__).parent.parent.parent
                voice_dir = base_dir.parent / "amiya_voice"
        self.voice_dir = Path(voice_dir)

        self.output_dir = Path(__file__).parent.parent.parent / "static" / "amiya_cache"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.voice_mappings = {
            "hello": ["问候.wav"],
            "idle": ["闲置.wav"],
            "confirm": ["信赖提升后交谈1.wav"],
            "report": ["任命助理 (1).wav"],
            "celebrate": ["周年庆典.wav"],
            "promote": ["精英化晋升2.wav"],
            "add_team": ["编入队伍.wav"],
            "battle_end": ["非3星结束行动.wav"],
            "title": ["标题.wav"],
            "talk": ["交谈1.wav"],
        }

        self._client = None
        self._reference_data_uri = None
        self._is_playing = False

        if _OPENAI_AVAILABLE:
            self._init_client()

        logger.info(f"阿米娅语音目录: {self.voice_dir}, 存在: {self.voice_dir.exists()}")
        logger.info(f"缓存目录: {self.output_dir}")

    def _init_client(self):
        api_key = os.environ.get("MIMO_API_KEY", self.MIMO_API_KEY)
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.MIMO_BASE_URL,
        )
        logger.info("MiMo VoiceClone 客户端初始化成功")

    def _get_reference_data_uri(self) -> Optional[str]:
        if self._reference_data_uri is not None:
            return self._reference_data_uri

        ref_path = self.voice_dir / self.REFERENCE_VOICE
        if not ref_path.exists():
            for name in ["交谈1.wav", "信赖提升后交谈1.wav", "干员报到.wav"]:
                alt = self.voice_dir / name
                if alt.exists():
                    ref_path = alt
                    break

        if not ref_path.exists():
            logger.error(f"参考音频不存在: {ref_path}")
            return None

        try:
            with open(str(ref_path), "rb") as f:
                voice_bytes = f.read()

            voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")
            ext = ref_path.suffix.lower()
            mime_type = "audio/wav" if ext == ".wav" else "audio/mpeg"
            self._reference_data_uri = f"data:{mime_type};base64,{voice_base64}"

            size_mb = len(voice_bytes) / (1024 * 1024)
            logger.info(f"参考音频已加载: {ref_path.name} ({size_mb:.1f}MB)")
            return self._reference_data_uri
        except Exception as e:
            logger.error(f"加载参考音频失败: {e}")
            return None

    def pre_synthesize(self) -> Dict[str, str]:
        """预合成常用语音，返回 {text: audio_file_name}"""
        results = {}
        for text in list(self.PRESET_TEXTS.keys()):
            cached = self._get_cached(text)
            if cached and cached.exists():
                results[text] = cached.name
                logger.info(f"预合成跳过(已有缓存): '{text}' -> {cached.name}")
                continue

            result = self._synthesize_new(text)
            if result.get("success") and result.get("audio_file"):
                results[text] = result["audio_file"]
                logger.info(f"预合成完成: '{text}' -> {result['audio_file']}")
            else:
                logger.warning(f"预合成失败: '{text}' -> {result.get('message', '未知错误')}")

        return results

    def get_audio_url(self, text: str = "博士，我在") -> Optional[str]:
        text = text.strip() or "博士，我在"
        cached = self._get_cached(text)
        if cached and cached.exists():
            return f"/api/voice/amiya/audio/{cached.name}"
        return None

    def get_random_encouragement(self) -> Optional[dict]:
        import random
        available = []
        for text in self.ENCOURAGEMENT_TEXTS:
            url = self.get_audio_url(text)
            if url:
                available.append({"text": text, "audio_url": url})
        if not available:
            return None
        return random.choice(available)

    def get_random_greeting(self) -> Optional[dict]:
        import random
        available = []
        for text in self.GREETING_TEXTS:
            url = self.get_audio_url(text)
            if url:
                available.append({"text": text, "audio_url": url})
        if not available:
            return None
        return random.choice(available)

    def get_random_focus_reminder(self) -> Optional[dict]:
        import random
        available = []
        for text in self.FOCUS_REMINDER_TEXTS:
            url = self.get_audio_url(text)
            if url:
                available.append({"text": text, "audio_url": url})
        if not available:
            return None
        return random.choice(available)

    def synthesize(self, text: str, force_synthesize: bool = False) -> dict:
        text = text.strip()
        if not text:
            text = "博士，我在"

        if not force_synthesize:
            matched_voice = self._match_keyword(text)
            if matched_voice:
                voice_path = self._get_voice_path(matched_voice)
                if voice_path:
                    return {
                        "success": True,
                        "message": "播放预定义语音",
                        "type": "preset",
                        "voice": matched_voice,
                        "audio_file": voice_path.name,
                        "audio_url": f"/api/voice/amiya/audio/{voice_path.name}"
                    }

        cached = self._get_cached(text)
        if cached:
            return {
                "success": True,
                "message": "使用缓存语音",
                "type": "cached",
                "audio_file": cached.name,
                "audio_url": f"/api/voice/amiya/audio/{cached.name}"
            }

        result = self._synthesize_new(text)
        if result.get("success"):
            return result

        fallback = self._get_fallback(text)
        if fallback:
            logger.warning(f"MiMo合成失败({result.get('message','?')}), 降级使用: {fallback['type']}")
            return fallback

        return result

    def _get_fallback(self, text: str) -> Optional[dict]:
        cached = self._get_cached(text)
        if cached and cached.exists():
            return {
                "success": True,
                "message": "降级-缓存语音",
                "type": "fallback_cached",
                "audio_file": cached.name,
                "audio_url": f"/api/voice/amiya/audio/{cached.name}"
            }
        for preset_key in ["hello", "talk", "idle"]:
            matched_voice = self._match_keyword(text)
            if matched_voice:
                voice_path = self._get_voice_path(matched_voice)
                if voice_path:
                    return {
                        "success": True,
                        "message": "降级-预设语音",
                        "type": "fallback_preset",
                        "voice": matched_voice,
                        "audio_file": voice_path.name,
                        "audio_url": f"/api/voice/amiya/audio/{voice_path.name}"
                    }
        return None

    def _get_cached(self, text: str) -> Optional[Path]:
        h = self._text_hash(text)
        for ext in [".wav", ".mp3"]:
            cached = self.output_dir / f"amiya_{h}{ext}"
            if cached.exists():
                return cached
        return None

    def _text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]

    def _synthesize_new(self, text: str) -> dict:
        if not _OPENAI_AVAILABLE or not self._client:
            return {"success": False, "message": "MiMo VoiceClone 不可用（openai SDK 未安装）"}

        voice_data_uri = self._get_reference_data_uri()
        if not voice_data_uri:
            return {"success": False, "message": "参考音频加载失败"}

        h = self._text_hash(text)
        output_path = self.output_dir / f"amiya_{h}.wav"

        try:
            styled_text = f"(平静，干脆){text}"
            completion = self._client.chat.completions.create(
                model=self.MIMO_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": self.AMIYA_STYLE
                    },
                    {
                        "role": "assistant",
                        "content": styled_text
                    }
                ],
                audio={
                    "format": "wav",
                    "voice": voice_data_uri
                }
            )

            message = completion.choices[0].message
            audio_bytes = base64.b64decode(message.audio.data)

            with open(str(output_path), "wb") as f:
                f.write(audio_bytes)

            size_kb = len(audio_bytes) / 1024
            logger.info(f"MiMo VoiceClone 合成完成: '{text}' -> {output_path.name} ({size_kb:.1f}KB)")

            return {
                "success": True,
                "message": "阿米娅声线合成完成（MiMo VoiceClone）",
                "type": "synthesized",
                "audio_file": output_path.name,
                "audio_url": f"/api/voice/amiya/audio/{output_path.name}"
            }
        except Exception as e:
            logger.error(f"MiMo VoiceClone 合成失败: {e}")
            return {"success": False, "message": str(e)}

    def _match_keyword(self, text: str) -> Optional[str]:
        keyword_map = {
            "hello": ["博士", "在", "叫", "回来"],
            "greeting": ["你好", "嗨", "早上好"],
            "idle": ["闲置", "无聊"],
            "confirm": ["确认", "好的", "明白"],
            "celebrate": ["庆祝", "恭喜"],
            "promote": ["晋升", "升级"],
            "add_team": ["组队", "加入"],
            "battle_end": ["结束", "胜利"],
            "title": ["标题", "开始"],
            "talk": ["聊天", "说话"],
        }
        text_lower = text.strip()
        for voice_name, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text_lower:
                    return voice_name
        return None

    def _get_voice_path(self, voice_name: str) -> Optional[Path]:
        if voice_name in self.voice_mappings:
            for filename in self.voice_mappings[voice_name]:
                path = self.voice_dir / filename
                if path.exists():
                    return path
        path = self.voice_dir / f"{voice_name}.wav"
        return path if path.exists() else None

    def get_available_voices(self) -> list:
        voices = []
        for key, filenames in self.voice_mappings.items():
            available = [f for f in filenames if (self.voice_dir / f).exists()]
            if available:
                voices.append({"name": key, "files": available})
        return voices

    def is_playing(self) -> bool:
        return self._is_playing

    def stop(self):
        self._is_playing = False