import logging
from typing import Callable, Optional
from core.models import TrafficJob, JobStatus, NetworkState
from core.state_manager import NetworkFSM, FSMValidationError
from drivers import get_driver

logger = logging.getLogger("TrafficExecutor")


class TrafficExecutor:
    """
    Motor de Execução Closed-Loop (Malha Fechada).
    Implementa a orquestração segura com Pre-Check, Commit Confirmed e Post-Check.
    """

    def __init__(self, current_network_state: NetworkState = NetworkState.NORMAL_DEFAULT):
        self.current_state = current_network_state

    async def execute_job(
        self,
        job: TrafficJob,
        lock_manager,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        async def notify(msg: str):
            logger.info(f"[{job.job_id}] {msg}")
            if status_callback:
                await status_callback(msg)

        # 1. Validação da Máquina de Estados Finita (FSM)
        try:
            NetworkFSM.validate_transition(self.current_state, job.action)
        except FSMValidationError as err:
            await notify(f"❌ Erro de Validação: {err}")
            job.status = JobStatus.DEADLOCK_ABORTED
            return False

        # 2. Aquisição de Lock Distribuído
        await notify(f"⏳ Adquirindo Lock Distribuído para {job.target_router_ip}...")
        acquired = await lock_manager.acquire()
        if not acquired:
            await notify("⚠️ Falha: Roteador ocupado ou bloqueado por Anti-Flap. Tente novamente mais tarde.")
            job.status = JobStatus.DEADLOCK_ABORTED
            return False

        driver = get_driver(
            job.vendor,
            host=job.target_router_ip,
            port=job.target_router_port,
            username=job.username,
            password=job.password or ""
        )

        try:
            # 3. Conexão e Pre-Check Baseline
            job.status = JobStatus.PRE_CHECK
            await notify("🔍 Conectando ao roteador e coletando telemetria inicial (Pre-Check)...")
            await driver.connect()
            baseline = await driver.pre_check_baseline()

            # 4. Aplicação Segura com Commit Confirmed (Dead Man's Switch)
            job.status = JobStatus.APPLYING_SAFE_COMMIT
            await notify(f"⚙️ Aplicando manobra: '{job.action.value}' com auto-reversão ativa (Commit Confirmed)...")
            await driver.apply_traffic_shift(job.action, safe_timer_seconds=180)

            # 5. Janela de Observação e Post-Check de Telemetria
            job.status = JobStatus.POST_CHECK_TELEMETRY
            await notify("📊 Aguardando convergência e validando telemetria em tempo real (Post-Check)...")
            success = await driver.post_check_telemetry(baseline)

            if success:
                # 6. Sucesso: Confirma Commit e Atualiza FSM
                job.status = JobStatus.CONFIRMING_COMMIT
                await notify("✅ Telemetria confirmada! Consolidando alteração no roteador (Confirm Commit)...")
                await driver.confirm_commit()

                self.current_state = NetworkFSM.get_target_state(job.action)
                job.status = JobStatus.COMPLETED
                await notify(f"🎉 Manobra concluída com SUCESSO! Novo estado da rede: {self.current_state.value}")
                return True
            else:
                # 7. Falha na telemetria: Executa Rollback Imediato
                job.status = JobStatus.FAILED_ROLLED_BACK
                await notify("⚠️ Telemetria não atingiu o objetivo! Acionando Rollback de emergência...")
                await driver.rollback()
                self.current_state = NetworkState.FAILED_DIRTY
                await notify("❌ Manobra abortada e revertida. Estado marcado como FAILED_DIRTY (requer atenção).")
                return False

        except Exception as e:
            logger.exception(f"Erro inesperado durante a execução do job {job.job_id}: {e}")
            job.status = JobStatus.FAILED_ROLLED_BACK
            await notify(f"💥 Falha de execução: {e}. Desfazendo alterações...")
            try:
                await driver.rollback()
            except Exception as rb_err:
                logger.error(f"Erro durante rollback: {rb_err}")
            self.current_state = NetworkState.FAILED_DIRTY
            return False

        finally:
            # 8. Desconecta do Roteador e Libera Lock Distribuído
            try:
                await driver.disconnect()
            except Exception:
                pass
            await lock_manager.release()
            await notify("🔓 Lock do roteador liberado.")
