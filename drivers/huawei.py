import asyncio
import logging
from typing import Dict, Any
from drivers.base import BaseNetworkDriver
from core.models import ActionType

logger = logging.getLogger("HuaweiDriver")


class HuaweiDriver(BaseNetworkDriver):
    """
    Driver para Huawei VRP / NE40E.
    Implementa Rollback transacional via 'commit trial <segundos>'.
    """

    def __init__(self, host: str, port: int = 22, username: str = "huawei", password: str = "Huawei@123"):
        super().__init__(host, port, username, password)

    async def connect(self):
        logger.info(f"[Huawei] Conectando via SSH a {self.host}:{self.port}...")
        await asyncio.sleep(0.5)
        logger.info(f"[Huawei] Conectado ao NE40E em {self.host}.")

    async def disconnect(self):
        logger.info(f"[Huawei] Desconectando de {self.host}...")
        await asyncio.sleep(0.1)

    async def pre_check_baseline(self) -> Dict[str, Any]:
        logger.info("[Huawei] Pre-Check: 'display bgp peer' e 'display interface brief'...")
        await asyncio.sleep(0.5)
        return {
            "bgp_peer_state": "Established",
            "traffic_op1_mbps": 600.0,
            "traffic_op2_mbps": 250.0,
        }

    async def apply_traffic_shift(self, action: ActionType, safe_timer_seconds: int = 180):
        logger.info("[Huawei] system-view -> bgp 65100...")

        if action == ActionType.SHUNT_TO_OP2:
            logger.info("[Huawei] peer 100.64.1.1 route-policy PREPEND_3X export")
        elif action == ActionType.SHUNT_TO_OP1:
            logger.info("[Huawei] peer 100.64.2.1 route-policy PREPEND_3X export")
        elif action == ActionType.ROLLBACK_DEFAULT:
            logger.info("[Huawei] undo peer 100.64.1.1 route-policy export")
            logger.info("[Huawei] undo peer 100.64.2.1 route-policy export")

        logger.info(f"[Huawei] Executando 'commit trial {safe_timer_seconds}' (Dead Man's Switch ativo)...")
        await asyncio.sleep(0.5)

    async def post_check_telemetry(self, baseline: Dict[str, Any]) -> bool:
        logger.info("[Huawei] Post-Check: 'display bgp routing-table' e contadores...")
        await asyncio.sleep(2.0)
        return True

    async def confirm_commit(self):
        logger.info("[Huawei] Confirm Commit: Executando 'commit' final (transação consolidada).")
        await asyncio.sleep(0.2)

    async def rollback(self):
        logger.warning("[Huawei] Executando 'abort' para descartar trial imediatamente!")
        await asyncio.sleep(0.5)
