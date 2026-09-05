import asyncio
import logging
from typing import Dict, Any
from drivers.base import BaseNetworkDriver
from core.models import ActionType

logger = logging.getLogger("CiscoDriver")


class CiscoDriver(BaseNetworkDriver):
    """
    Driver para Cisco IOS / IOS-XE / IOL.
    Implementa Rollback via Cisco Archive ('configure replace ... revert trigger timer').
    """

    def __init__(self, host: str, port: int = 22, username: str = "cisco", password: str = "cisco"):
        super().__init__(host, port, username, password)

    async def connect(self):
        logger.info(f"[Cisco] Conectando via SSH a {self.host}:{self.port}...")
        await asyncio.sleep(0.5)
        logger.info(f"[Cisco] Conectado a {self.host}.")

    async def disconnect(self):
        logger.info(f"[Cisco] Desconectando de {self.host}...")
        await asyncio.sleep(0.1)

    async def pre_check_baseline(self) -> Dict[str, Any]:
        logger.info("[Cisco] Pre-Check: 'show ip bgp summary' e 'show interfaces'...")
        await asyncio.sleep(0.5)
        return {
            "bgp_established": True,
            "traffic_op1_mbps": 500.0,
            "traffic_op2_mbps": 200.0,
        }

    async def apply_traffic_shift(self, action: ActionType, safe_timer_seconds: int = 180):
        timer_min = max(1, safe_timer_seconds // 60)
        logger.info(f"[Cisco] Arming rollback timer: 'configure replace flash:backup.cfg revert trigger timer {timer_min}'")
        await asyncio.sleep(0.3)

        if action == ActionType.SHUNT_TO_OP2:
            logger.info("[Cisco] Aplicando route-map PREPEND_OUT para neighbor Operadora 1...")
            logger.info("[Cisco] Executando 'clear ip bgp * soft out'...")
        elif action == ActionType.SHUNT_TO_OP1:
            logger.info("[Cisco] Aplicando route-map PREPEND_OUT para neighbor Operadora 2...")
            logger.info("[Cisco] Executando 'clear ip bgp * soft out'...")
        elif action == ActionType.ROLLBACK_DEFAULT:
            logger.info("[Cisco] Restaurando route-maps padrão...")

        await asyncio.sleep(0.5)

    async def post_check_telemetry(self, baseline: Dict[str, Any]) -> bool:
        logger.info("[Cisco] Post-Check: Validando convergência da tabela BGP...")
        await asyncio.sleep(2.0)
        return True

    async def confirm_commit(self):
        logger.info("[Cisco] Confirm Commit: Enviando 'configure confirm' para consolidar alteração.")
        await asyncio.sleep(0.2)

    async def rollback(self):
        logger.warning("[Cisco] Executando 'configure replace flash:backup.cfg force' imediato!")
        await asyncio.sleep(0.5)
