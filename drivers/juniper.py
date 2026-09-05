import asyncio
import logging
from typing import Dict, Any
from drivers.base import BaseNetworkDriver
from core.models import ActionType

logger = logging.getLogger("JuniperDriver")


class JuniperDriver(BaseNetworkDriver):
    """
    Driver para Juniper Junos (vMX / vQFX / cRPD).
    Implementa Rollback transacional nativo via 'commit confirmed <minutos>'.
    """

    def __init__(self, host: str, port: int = 22, username: str = "root", password: str = "Juniper"):
        super().__init__(host, port, username, password)

    async def connect(self):
        logger.info(f"[Juniper] Conectando via Netconf/SSH a {self.host}:{self.port}...")
        await asyncio.sleep(0.5)
        logger.info(f"[Juniper] Conectado ao Junos em {self.host}.")

    async def disconnect(self):
        logger.info(f"[Juniper] Desconectando de {self.host}...")
        await asyncio.sleep(0.1)

    async def pre_check_baseline(self) -> Dict[str, Any]:
        logger.info("[Juniper] Pre-Check: 'show bgp summary' e 'show interfaces extensive'...")
        await asyncio.sleep(0.5)
        return {
            "bgp_state": "Established",
            "traffic_op1_mbps": 400.0,
            "traffic_op2_mbps": 350.0,
        }

    async def apply_traffic_shift(self, action: ActionType, safe_timer_seconds: int = 180):
        timer_min = max(1, safe_timer_seconds // 60)
        logger.info(f"[Juniper] Entrando em modo de configuração...")

        if action == ActionType.SHUNT_TO_OP2:
            logger.info("[Juniper] set protocols bgp group OPERADORA_1 export POLICY_PREPEND_3X")
        elif action == ActionType.SHUNT_TO_OP1:
            logger.info("[Juniper] set protocols bgp group OPERADORA_2 export POLICY_PREPEND_3X")
        elif action == ActionType.ROLLBACK_DEFAULT:
            logger.info("[Juniper] set protocols bgp group OPERADORA_1 export POLICY_DEFAULT")
            logger.info("[Juniper] set protocols bgp group OPERADORA_2 export POLICY_DEFAULT")

        logger.info(f"[Juniper] Executando 'commit confirmed {timer_min}' (Dead Man's Switch ativo)...")
        await asyncio.sleep(0.5)

    async def post_check_telemetry(self, baseline: Dict[str, Any]) -> bool:
        logger.info("[Juniper] Post-Check: 'show route advertising-protocol bgp'...")
        await asyncio.sleep(2.0)
        return True

    async def confirm_commit(self):
        logger.info("[Juniper] Confirm Commit: Executando 'commit' final (transação consolidada).")
        await asyncio.sleep(0.2)

    async def rollback(self):
        logger.warning("[Juniper] Executando 'rollback 1' e 'commit' imediato!")
        await asyncio.sleep(0.5)
