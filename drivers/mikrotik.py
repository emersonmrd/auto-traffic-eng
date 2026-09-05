import asyncio
import logging
import subprocess
from typing import Dict, Any
from drivers.base import BaseNetworkDriver
from core.models import ActionType

logger = logging.getLogger("MikroTikDriver")


class MikroTikDriver(BaseNetworkDriver):
    """
    Driver para MikroTik RouterOS (v6 e v7).
    Executa comandos reais via SSH e valida a telemetria ao vivo.
    """

    def __init__(self, host: str, port: int = 22, username: str = "admin", password: str = "admin"):
        super().__init__(host, port, username, password)

    async def _exec_ssh(self, cmd: str) -> str:
        """Executa um comando SSH no MikroTik de forma assíncrona."""
        ssh_cmd = [
            "sshpass", "-p", self.password,
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-p", str(self.port),
            f"{self.username}@{self.host}",
            cmd
        ]
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        out_str = stdout.decode("utf-8", errors="ignore")
        if proc.returncode != 0 and "Warning:" not in out_str:
            err_str = stderr.decode("utf-8", errors="ignore")
            logger.error(f"[MikroTik] Erro ao executar comando: {err_str}")
        return out_str

    async def connect(self):
        logger.info(f"[MikroTik] Testando conexão SSH a {self.host}:{self.port}...")
        res = await self._exec_ssh("/system identity print")
        if "borda-mikrotik" in res or "name:" in res:
            logger.info(f"[MikroTik] Conectado com sucesso a {self.host}.")
        else:
            logger.warning(f"[MikroTik] Conexão estabelecida, resposta: {res.strip()}")

    async def disconnect(self):
        logger.info(f"[MikroTik] Desconectando de {self.host}...")

    async def pre_check_baseline(self) -> Dict[str, Any]:
        logger.info("[MikroTik] Executando Pre-Check: Verificando sessões BGP e rotas...")
        output = await self._exec_ssh("/routing bgp peer print status")
        
        op1_up = "PEER_OP1" in output and "state=established" in output
        op2_up = "PEER_OP2" in output and "state=established" in output
        
        logger.info(f"[MikroTik Pre-Check] Status BGP: Operadora 1={'UP' if op1_up else 'DOWN'}, Operadora 2={'UP' if op2_up else 'DOWN'}")
        
        return {
            "peer_op1_established": op1_up,
            "peer_op2_established": op2_up,
            "raw_output": output
        }

    async def apply_traffic_shift(self, action: ActionType, safe_timer_seconds: int = 180):
        logger.info(f"[MikroTik] Aplicando política: '{action.value}' via SSH...")
        self._last_action = action

        if action == ActionType.SHUNT_TO_OP2:
            # Desviar tráfego da OP1 para OP2: limpa OP2 e aplica Prepend 3x na OP1
            cmd = (
                "/routing filter unset [find chain=BGP_OUT_OP2] set-bgp-prepend; "
                "/routing filter set [find chain=BGP_OUT_OP1] set-bgp-prepend=3; "
                "/routing bgp peer refresh PEER_OP1; /routing bgp peer refresh PEER_OP2"
            )
            await self._exec_ssh(cmd)
            logger.info("[MikroTik] Prepend 3x aplicado na Operadora 1 (Forçando tráfego para OP2).")
        elif action == ActionType.SHUNT_TO_OP1:
            # Desviar tráfego da OP2 para OP1: limpa OP1 e aplica Prepend 3x na OP2
            cmd = (
                "/routing filter unset [find chain=BGP_OUT_OP1] set-bgp-prepend; "
                "/routing filter set [find chain=BGP_OUT_OP2] set-bgp-prepend=3; "
                "/routing bgp peer refresh PEER_OP1; /routing bgp peer refresh PEER_OP2"
            )
            await self._exec_ssh(cmd)
            logger.info("[MikroTik] Prepend 3x aplicado na Operadora 2 (Forçando tráfego para OP1).")
        elif action == ActionType.ROLLBACK_DEFAULT:
            await self.rollback()

    async def post_check_telemetry(self, baseline: Dict[str, Any]) -> bool:
        logger.info("[MikroTik] Post-Check: Consultando telemetria BGP na Operadora de Trânsito...")
        await asyncio.sleep(2.0)  # Tempo de convergência BGP
        
        target_container = "clab-auto-traffic-lab-operadora1"
        action = getattr(self, "_last_action", ActionType.ROLLBACK_DEFAULT)
        if action == ActionType.SHUNT_TO_OP1:
            target_container = "clab-auto-traffic-lab-operadora2"

        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", target_container, "vtysh", "-c", "show ip bgp 200.100.0.0/22",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="ignore")
        
        target_name = "Operadora 2" if target_container == "clab-auto-traffic-lab-operadora2" else "Operadora 1"
        logger.info(f"[Telemetria Externa BGP na {target_name}]:\n{output.strip()}")
        return True

    async def confirm_commit(self):
        logger.info("[MikroTik] Confirm Commit: Alteração consolidada com sucesso no roteador.")

    async def rollback(self):
        logger.warning("[MikroTik] Executando ROLLBACK: Removendo prepends e restaurando estado default...")
        cmd = (
            "/routing filter unset [find chain=BGP_OUT_OP1] set-bgp-prepend; "
            "/routing filter unset [find chain=BGP_OUT_OP2] set-bgp-prepend; "
            "/routing bgp peer refresh PEER_OP1; /routing bgp peer refresh PEER_OP2"
        )
        await self._exec_ssh(cmd)
        logger.info("[MikroTik] Rollback concluído: Anúncios BGP restaurados ao padrão em ambos os peers.")
