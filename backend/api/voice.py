import logging
import os
import tempfile
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_voice_manager = None
_tts_output_dir = Path(__file__).parent.parent / "static" / "tts"
_tts_output_dir.mkdir(parents=True, exist_ok=True)

_AMIYA_VOICE_DIR = Path("d:/Vibe_Coidng/StudyRoom/amiya_voice")
_AMIYA_CACHE_DIR = Path(__file__).parent.parent / "static" / "amiya_cache"


def get_voice_manager():
    global _voice_manager
    if _voice_manager is None:
        from modules.voice import VoiceManager
        _voice_manager = VoiceManager()
    return _voice_manager


class TTSRequest(BaseModel):
    text: str
    rate: int = 180
    volume: float = 0.9


@router.post("/wakeup")
async def wakeup_detect(audio: UploadFile = File(...)):
    """唤醒词检测"""
    try:
        contents = await audio.read()
        vm = get_voice_manager()
        if vm.vad:
            speech_ratio = vm.vad.process_audio(contents)
            if speech_ratio < 0.1:
                return {"success": True, "data": {"detected": False, "keyword": None, "speech_ratio": speech_ratio}}

        if vm.asr and speech_ratio > 0.1:
            asr_result = vm.asr.transcribe_audio_bytes(contents)
            text = asr_result.get("text", "")
            if text:
                wake_result = vm.wake_word_detector.detect(text)
                return {"success": True, "data": {**wake_result, "text": text}}

        return {"success": True, "data": {"detected": False, "keyword": None, "text": ""}}
    except Exception as e:
        logger.error(f"唤醒词检测失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/asr")
async def speech_to_text(audio: UploadFile = File(...), language: str = Query("zh")):
    """语音识别"""
    try:
        contents = await audio.read()
        vm = get_voice_manager()
        if not vm.asr:
            return {"success": False, "message": "ASR引擎不可用"}

        import tempfile, os, uuid
        from pathlib import Path
        tmp_dir = Path(tempfile.gettempdir()) / "smartstudypal_asr"
        tmp_dir.mkdir(exist_ok=True)
        suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
        tmp_path = tmp_dir / f"asr_{uuid.uuid4().hex[:8]}{suffix}"
        with open(tmp_path, "wb") as f:
            f.write(contents)

        result = vm.asr.transcribe(str(tmp_path), language=language)

        try:
            os.remove(tmp_path)
        except Exception:
            pass

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """文字转语音"""
    try:
        vm = get_voice_manager()
        if not vm.tts:
            return {"success": False, "message": "TTS引擎不可用"}

        vm.tts.set_rate(req.rate)
        vm.tts.set_volume(req.volume)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = _tts_output_dir / f"tts_{timestamp}.wav"

        vm.tts.save_to_file(req.text, str(output_path))

        if output_path.exists():
            return {
                "success": True,
                "data": {
                    "file_url": f"/static/tts/{output_path.name}",
                    "text": req.text,
                }
            }
        return {"success": False, "message": "语音文件生成失败"}
    except Exception as e:
        logger.error(f"TTS失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/tts/voices")
async def get_voice_list():
    """获取可用语音列表"""
    try:
        vm = get_voice_manager()
        if not vm.tts:
            return {"success": False, "message": "TTS引擎不可用"}
        voices = vm.tts.get_voices()
        return {"success": True, "data": voices}
    except Exception as e:
        logger.error(f"获取语音列表失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/emotion")
async def emotion_analyze(audio: UploadFile = File(...)):
    """语音情绪分析"""
    try:
        contents = await audio.read()
        vm = get_voice_manager()
        if not vm.emotion_classifier:
            return {"success": False, "message": "情绪分类器不可用"}

        import numpy as np
        audio_np = np.frombuffer(contents, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio_np) < 8000:
            return {"success": False, "message": "音频过短，无法分析情绪"}

        result = vm.emotion_classifier.classify(audio_np)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"情绪分析失败: {e}")
        return {"success": False, "message": str(e)}


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """WebSocket语音流"""
    await websocket.accept()
    logger.info("语音WebSocket连接已建立")
    try:
        while True:
            data = await websocket.receive_bytes()
            vm = get_voice_manager()
            result = vm.process_audio(data)
            await websocket.send_json({"success": True, "data": result})
    except WebSocketDisconnect:
        logger.info("语音WebSocket连接已断开")
    except Exception as e:
        logger.error(f"语音WebSocket错误: {e}")


@router.post("/process")
async def process_voice(audio: UploadFile = File(...)):
    """处理语音（兼容旧接口）"""
    try:
        contents = await audio.read()
        vm = get_voice_manager()
        result = vm.process_audio(contents)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/amiya/audio/{filename}")
async def get_amiya_audio(filename: str):
    """获取阿米娅语音文件（支持原始语音和缓存合成语音）"""
    voice_path = _AMIYA_VOICE_DIR / filename
    if voice_path.exists():
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return FileResponse(path=str(voice_path), media_type=media_type, filename=filename)

    cache_path = _AMIYA_CACHE_DIR / filename
    if cache_path.exists():
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return FileResponse(path=str(cache_path), media_type=media_type, filename=filename)

    return {"success": False, "message": f"文件不存在: {filename}"}


@router.get("/amiya/ready")
async def get_amiya_ready_audio(text: str = Query("博士，我在")):
    """获取已预合成的阿米娅音频URL（快速响应，不触发合成）"""
    try:
        vm = get_voice_manager()
        if vm.amiya_tts:
            audio_url = vm.amiya_tts.get_audio_url(text)
            if audio_url:
                return {"success": True, "data": {"audio_url": audio_url, "cached": True}}
        return {"success": True, "data": {"audio_url": None, "cached": False}}
    except Exception as e:
        return {"success": True, "data": {"audio_url": None, "cached": False, "error": str(e)}}


@router.get("/amiya/encouragement")
async def get_amiya_encouragement():
    """随机获取阿米娅鼓励学习语音"""
    try:
        vm = get_voice_manager()
        if vm.amiya_tts:
            result = vm.amiya_tts.get_random_encouragement()
            if result:
                return {"success": True, "data": result}
        return {"success": False, "message": "鼓励语音未就绪"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/amiya/greeting")
async def get_amiya_greeting():
    """随机获取阿米娅打招呼语音"""
    try:
        vm = get_voice_manager()
        if vm.amiya_tts:
            result = vm.amiya_tts.get_random_greeting()
            if result:
                return {"success": True, "data": result}
        return {"success": False, "message": "打招呼语音未就绪"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/amiya/speak")
async def amiya_speak(text: str = Query(None), force_synthesize: bool = Query(False)):
    """
    阿米娅语音合成
    
    Args:
        text: 要合成的文本，默认为 "博士，我在"
        force_synthesize: 是否强制使用TTS合成（跳过预设语音匹配）
    
    Returns:
        dict: 合成结果，包含 audio_url 用于前端播放
    """
    try:
        logger.info(f"收到阿米娅语音请求: {text}, force_synthesize={force_synthesize}")
        vm = get_voice_manager()
        result = vm.amiya_speak(text, force_synthesize=force_synthesize)
        
        if result.get("success") and result.get("audio_file"):
            result["audio_url"] = f"/api/voice/amiya/audio/{result['audio_file']}"
        
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"阿米娅语音合成失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/amiya/voices")
async def get_amiya_voices():
    """获取阿米娅可用语音列表"""
    try:
        vm = get_voice_manager()
        voices = vm.get_amiya_voices()
        return {"success": True, "data": voices}
    except Exception as e:
        logger.error(f"获取阿米娅语音列表失败: {e}")
        return {"success": False, "message": str(e)}
