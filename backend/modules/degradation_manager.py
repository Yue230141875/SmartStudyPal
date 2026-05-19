import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ServiceLevel(Enum):
    FULL = "full"
    DEGRADED = "degraded"
    MINIMAL = "minimal"
    OFFLINE = "offline"


class ServiceStatus:
    def __init__(self, name: str, level: ServiceLevel = ServiceLevel.FULL,
                 message: str = "", last_check: datetime = None):
        self.name = name
        self.level = level
        self.message = message
        self.last_check = last_check or datetime.now()
        self.error_count = 0
        self.success_count = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level.value,
            "message": self.message,
            "last_check": self.last_check.isoformat(),
            "error_count": self.error_count,
            "success_count": self.success_count,
        }


class DegradationManager:
    """降级策略管理器：监控服务健康状态，自动降级和恢复"""

    def __init__(self, max_errors: int = 5, recovery_threshold: int = 3):
        self.max_errors = max_errors
        self.recovery_threshold = recovery_threshold
        self.services: Dict[str, ServiceStatus] = {}
        self._consecutive_success = {}
        logger.info(f"降级管理器初始化: max_errors={max_errors}, recovery_threshold={recovery_threshold}")

    def register_service(self, name: str, initial_level: ServiceLevel = ServiceLevel.FULL):
        """注册服务"""
        self.services[name] = ServiceStatus(name=name, level=initial_level)
        self._consecutive_success[name] = 0
        logger.info(f"注册服务: {name}, 初始级别: {initial_level.value}")

    def report_success(self, service_name: str, message: str = ""):
        """报告服务成功"""
        if service_name not in self.services:
            logger.warning(f"未注册的服务: {service_name}")
            return

        status = self.services[service_name]
        status.success_count += 1
        status.last_check = datetime.now()
        status.message = message

        self._consecutive_success[service_name] = self._consecutive_success.get(service_name, 0) + 1

        if status.level != ServiceLevel.FULL:
            if self._consecutive_success[service_name] >= self.recovery_threshold:
                old_level = status.level
                if status.level == ServiceLevel.OFFLINE:
                    status.level = ServiceLevel.MINIMAL
                elif status.level == ServiceLevel.MINIMAL:
                    status.level = ServiceLevel.DEGRADED
                elif status.level == ServiceLevel.DEGRADED:
                    status.level = ServiceLevel.FULL
                self._consecutive_success[service_name] = 0
                logger.info(f"服务恢复: {service_name} {old_level.value} -> {status.level.value}")

    def report_error(self, service_name: str, error: str = ""):
        """报告服务错误"""
        if service_name not in self.services:
            logger.warning(f"未注册的服务: {service_name}")
            return

        status = self.services[service_name]
        status.error_count += 1
        status.last_check = datetime.now()
        status.message = error
        self._consecutive_success[service_name] = 0

        if status.error_count >= self.max_errors:
            old_level = status.level
            if status.level == ServiceLevel.FULL:
                status.level = ServiceLevel.DEGRADED
            elif status.level == ServiceLevel.DEGRADED:
                status.level = ServiceLevel.MINIMAL
            elif status.level == ServiceLevel.MINIMAL:
                status.level = ServiceLevel.OFFLINE
            status.error_count = 0
            logger.warning(f"服务降级: {service_name} {old_level.value} -> {status.level.value}, 原因: {error}")

    def get_service_level(self, service_name: str) -> ServiceLevel:
        """获取服务级别"""
        if service_name in self.services:
            return self.services[service_name].level
        return ServiceLevel.OFFLINE

    def is_available(self, service_name: str, min_level: ServiceLevel = ServiceLevel.MINIMAL) -> bool:
        """检查服务是否可用"""
        level = self.get_service_level(service_name)
        level_order = {
            ServiceLevel.FULL: 4,
            ServiceLevel.DEGRADED: 3,
            ServiceLevel.MINIMAL: 2,
            ServiceLevel.OFFLINE: 1,
        }
        return level_order.get(level, 0) >= level_order.get(min_level, 0)

    def get_fusion_weights(self) -> dict:
        """根据服务状态动态调整融合权重"""
        vision_level = self.get_service_level("vision")
        voice_level = self.get_service_level("voice")

        if vision_level == ServiceLevel.FULL and voice_level == ServiceLevel.FULL:
            return {"vision": 0.7, "voice": 0.3}
        elif vision_level == ServiceLevel.FULL and voice_level != ServiceLevel.FULL:
            return {"vision": 0.9, "voice": 0.1}
        elif vision_level != ServiceLevel.FULL and voice_level == ServiceLevel.FULL:
            return {"vision": 0.3, "voice": 0.7}
        elif vision_level == ServiceLevel.OFFLINE and voice_level == ServiceLevel.OFFLINE:
            return {"vision": 0.5, "voice": 0.5}
        else:
            return {"vision": 0.6, "voice": 0.4}

    def get_all_status(self) -> dict:
        """获取所有服务状态"""
        return {
            "services": {name: s.to_dict() for name, s in self.services.items()},
            "fusion_weights": self.get_fusion_weights(),
            "overall": self._get_overall_level().value,
        }

    def _get_overall_level(self) -> ServiceLevel:
        """获取整体服务级别"""
        if not self.services:
            return ServiceLevel.OFFLINE
        levels = [s.level for s in self.services.values()]
        if all(l == ServiceLevel.FULL for l in levels):
            return ServiceLevel.FULL
        if any(l == ServiceLevel.OFFLINE for l in levels):
            return ServiceLevel.DEGRADED
        return ServiceLevel.DEGRADED


_degradation_manager = None


def get_degradation_manager() -> DegradationManager:
    """获取全局降级管理器"""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = DegradationManager()
        _degradation_manager.register_service("vision")
        _degradation_manager.register_service("voice")
        _degradation_manager.register_service("database")
    return _degradation_manager


def test():
    """降级管理器测试"""
    print("=== 降级策略管理器测试 ===")
    dm = DegradationManager(max_errors=3, recovery_threshold=2)
    dm.register_service("vision")
    dm.register_service("voice")

    print(f"初始状态: {dm.get_all_status()}")

    for i in range(4):
        dm.report_error("vision", f"摄像头错误 {i+1}")
        print(f"  vision 错误 {i+1}: level={dm.get_service_level('vision').value}")

    print(f"融合权重: {dm.get_fusion_weights()}")

    for i in range(3):
        dm.report_success("vision", f"恢复 {i+1}")
        print(f"  vision 恢复 {i+1}: level={dm.get_service_level('vision').value}")

    print(f"最终状态: {dm.get_all_status()}")
    print("[OK] 降级策略管理器测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
