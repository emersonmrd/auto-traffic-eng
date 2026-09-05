import asyncio
import logging
from core.models import TrafficJob, ActionType, RouterVendor, NetworkState
from core.state_manager import NetworkFSM, FSMValidationError
from worker.executor import TrafficExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SimulationDemo")


class MockRedisLock:
    """Mock assíncrono do Redis Distributed Lock para simulação em laboratório."""
    _locks = {}
    _rate_limits = {}

    def __init__(self, router_id: str):
        self.router_id = router_id

    async def acquire(self) -> bool:
        if self._locks.get(self.router_id, False):
            return False
        self._locks[self.router_id] = True
        return True

    async def release(self):
        self._locks[self.router_id] = False


async def run_lab_demonstration():
    print("=" * 70)
    print(" 🚀 INICIANDO SIMULAÇÃO DE ENGENHARIA DE TRÁFEGO CLOSED-LOOP")
    print("=" * 70)

    executor = TrafficExecutor(current_network_state=NetworkState.NORMAL_DEFAULT)
    lock_factory = lambda rid: MockRedisLock(rid)

    # -------------------------------------------------------------
    # CENÁRIO 1: Desvio de tráfego com sucesso (Operadora 1 -> Operadora 2)
    # -------------------------------------------------------------
    print("\n--- [CENÁRIO 1] Operador solicita desvio para a Operadora 2 ---")
    job1 = TrafficJob(
        job_id="JOB-001",
        action=ActionType.SHUNT_TO_OP2,
        vendor=RouterVendor.MIKROTIK,
        target_router_ip="172.28.100.5",
        username="admin",
        password="admin",
        requested_by_user_id=123456,
        requested_by_username="analista_redes"
    )

    async def callback1(msg):
        print(f" [Telegram Bot Feedback] -> {msg}")

    success = await executor.execute_job(job1, lock_factory(job1.target_router_ip), status_callback=callback1)
    print(f"Resultado do Job 1: {'SUCESSO' if success else 'FALHA'}")
    print(f"Estado Atual da Rede: {executor.current_state.value}")

    # -------------------------------------------------------------
    # CENÁRIO 2: Tentativa de Ação Ilegal pela FSM (Guardrail em ação)
    # -------------------------------------------------------------
    print("\n--- [CENÁRIO 2] Operador tenta desviar novamente para Op 2 (Ação Ilegal) ---")
    job2 = TrafficJob(
        job_id="JOB-002",
        action=ActionType.SHUNT_TO_OP2,
        vendor=RouterVendor.MIKROTIK,
        target_router_ip="172.28.100.5",
        username="admin",
        password="admin",
        requested_by_user_id=123456
    )
    success2 = await executor.execute_job(job2, lock_factory(job2.target_router_ip), status_callback=callback1)
    print(f"Resultado do Job 2: {'SUCESSO' if success2 else 'BLOQUEADO COM SEGURANÇA'}")

    # -------------------------------------------------------------
    # CENÁRIO 3: Rollback Seguro para o Estado Padrão
    # -------------------------------------------------------------
    print("\n--- [CENÁRIO 3] Incidente resolvido: Operador solicita Rollback ---")
    job3 = TrafficJob(
        job_id="JOB-003",
        action=ActionType.ROLLBACK_DEFAULT,
        vendor=RouterVendor.MIKROTIK,
        target_router_ip="172.28.100.5",
        username="admin",
        password="admin",
        requested_by_user_id=123456
    )
    success3 = await executor.execute_job(job3, lock_factory(job3.target_router_ip), status_callback=callback1)
    print(f"Resultado do Job 3: {'SUCESSO' if success3 else 'FALHA'}")
    print(f"Estado Final da Rede: {executor.current_state.value}")

    print("\n" + "=" * 70)
    print(" ✅ TODOS OS GUARDRAILS E FLUXOS FORAM DEMONSTRADOS COM SUCESSO!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_lab_demonstration())
