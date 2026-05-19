import logging
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter()


def cv2_imdecode(nparr: np.ndarray) -> np.ndarray:
    """安全解码图像"""
    import cv2
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame

_vision_manager = None
_latest_snapshot = {}


def get_vision_manager():
    global _vision_manager
    if _vision_manager is None:
        from modules.vision import VisionManager
        _vision_manager = VisionManager()
    return _vision_manager


@router.post("/detect")
async def detect_focus(image: UploadFile = File(...)):
    """上传单帧图像进行专注度检测"""
    try:
        logger.info(f"收到视觉检测请求，文件名: {image.filename}，大小: {image.size} bytes")
        contents = await image.read()
        logger.debug(f"读取图像数据完成，长度: {len(contents)}")
        
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2_imdecode(nparr)
        if frame is None:
            logger.error("无法解码图像")
            return {"success": False, "message": "无法解码图像"}
        
        logger.debug(f"图像解码成功，尺寸: {frame.shape}")

        vm = get_vision_manager()
        logger.debug(f"视觉管理器获取成功，vision_available: {vm._vision_available}")
        
        result = vm.process_frame(frame)
        logger.info(f"视觉检测完成，人脸检测: {result.get('face_detected', False)}, 专注度: {result.get('focus_score', 0)}")

        global _latest_snapshot
        _latest_snapshot = {
            **result,
            "timestamp": datetime.now().isoformat(),
        }

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"视觉检测失败: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


@router.get("/snapshot")
async def get_latest_snapshot():
    """获取最新快照"""
    if _latest_snapshot:
        return {"success": True, "data": _latest_snapshot}
    return {"success": False, "message": "暂无快照数据"}


@router.get("/config")
async def get_vision_config():
    """获取视觉模块配置"""
    vm = get_vision_manager()
    return {
        "success": True,
        "data": {
            "vision_available": vm._vision_available,
            "face_detector": vm.face_detector is not None,
            "pose_estimator": vm.pose_estimator is not None,
            "max_width": vm.preprocessor.max_width,
            "clip_limit": vm.preprocessor.clip_limit,
        }
    }


@router.post("/start")
async def start_detection():
    """启动视觉检测"""
    return {"success": True, "message": "视觉检测已启动"}


@router.post("/stop")
async def stop_detection():
    """停止视觉检测"""
    return {"success": True, "message": "视觉检测已停止"}


@router.get("/status")
async def get_focus_status():
    """获取当前专注度状态"""
    if _latest_snapshot:
        return {
            "score": _latest_snapshot.get("focus_score", 0),
            "label": _latest_snapshot.get("focus_level", "未知"),
            "timestamp": _latest_snapshot.get("timestamp", datetime.now().isoformat()),
        }
    return {"score": 0, "label": "未检测", "timestamp": datetime.now().isoformat()}


@router.websocket("/stream")
async def vision_stream(websocket: WebSocket):
    """WebSocket实时视觉流"""
    await websocket.accept()
    logger.info("视觉WebSocket连接已建立")
    try:
        while True:
            data = await websocket.receive_bytes()
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2_imdecode(nparr)
            if frame is not None:
                vm = get_vision_manager()
                result = vm.process_frame(frame)
                global _latest_snapshot
                _latest_snapshot = {**result, "timestamp": datetime.now().isoformat()}
                await websocket.send_json({"success": True, "data": result})
            else:
                await websocket.send_json({"success": False, "message": "无法解码帧"})
    except WebSocketDisconnect:
        logger.info("视觉WebSocket连接已断开")
    except Exception as e:
        logger.error(f"视觉WebSocket错误: {e}")
