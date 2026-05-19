import logging
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def health_check():
    """系统健康检查"""
    from modules.degradation_manager import get_degradation_manager
    dm = get_degradation_manager()
    status = dm.get_all_status()

    return {
        "status": "ok" if status["overall"] in ("full", "degraded") else "error",
        "timestamp": datetime.now().isoformat(),
        "services": status["services"],
        "fusion_weights": status["fusion_weights"],
        "overall_level": status["overall"],
    }


@router.get("/services/{service_name}")
async def service_health(service_name: str):
    """单个服务健康检查"""
    from modules.degradation_manager import get_degradation_manager
    dm = get_degradation_manager()

    if service_name not in dm.services:
        return {"status": "unknown", "service": service_name}

    s = dm.services[service_name]
    return {
        "status": s.level.value,
        "service": service_name,
        "message": s.message,
        "last_check": s.last_check.isoformat(),
        "error_count": s.error_count,
        "success_count": s.success_count,
    }


@router.get("/weights")
async def get_fusion_weights():
    """获取当前融合权重"""
    from modules.degradation_manager import get_degradation_manager
    dm = get_degradation_manager()
    return {"weights": dm.get_fusion_weights()}
