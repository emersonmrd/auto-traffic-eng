import asyncio
import uuid
import logging
from typing import Optional

logger = logging.getLogger("TrafficLock")

# Script Lua para liberação segura e atômica de Lock no Redis
LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Script Lua para renovação periódica (Heartbeat)
LUA_EXTEND_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("pexpire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class DistributedRouterLock:
    """
    Lock Distribuído com Lease (TTL), Watchdog (Auto-renovação) e Rate-Limiting Anti-Flap.
    Evita Deadlocks e bloqueia acessos concorrentes ao mesmo roteador.
    """

    def __init__(self, redis_client, router_id: str, lease_ttl_ms: int = 30000):
        self.redis = redis_client
        self.router_id = router_id
        self.lock_key = f"lock:router:{router_id}"
        self.rate_limit_key = f"ratelimit:router:{router_id}"
        self.lease_ttl_ms = lease_ttl_ms
        self.token = str(uuid.uuid4())
        self._watchdog_task: Optional[asyncio.Task] = None
        self._is_held = False

    async def acquire(self, anti_flap_seconds: int = 60) -> bool:
        """
        Tenta adquirir o lock de forma atômica no Redis.
        Também verifica o Rate-Limiting anti-flapping.
        """
        # 1. Verifica Rate-Limit anti-flapping
        if await self.redis.exists(self.rate_limit_key):
            ttl_remaining = await self.redis.ttl(self.rate_limit_key)
            logger.warning(
                f"Bloqueado por Anti-Flap no roteador {self.router_id}. Aguarde {ttl_remaining}s."
            )
            return False

        # 2. Adquire o Lock atômico com NX (Not Exists) e PX (TTL em ms)
        acquired = await self.redis.set(
            self.lock_key, self.token, nx=True, px=self.lease_ttl_ms
        )

        if not acquired:
            logger.warning(f"Roteador {self.router_id} já está bloqueado por outra execução!")
            return False

        self._is_held = True
        logger.info(f"Lock adquirido com sucesso para {self.router_id} (Token: {self.token[:8]}...)")

        # 3. Inicia o Watchdog em background para renovar o TTL enquanto a tarefa rodar
        self._watchdog_task = asyncio.create_task(self._heartbeat())

        # 4. Registra Rate-Limit para proteção BGP
        await self.redis.set(self.rate_limit_key, "ACTIVE", ex=anti_flap_seconds)

        return True

    async def _heartbeat(self):
        """Thread assíncrona que estende a vida do lock a cada 1/3 do TTL."""
        interval = (self.lease_ttl_ms / 1000.0) / 3.0
        try:
            while self._is_held:
                await asyncio.sleep(interval)
                result = await self.redis.eval(
                    LUA_EXTEND_LOCK, 1, self.lock_key, self.token, self.lease_ttl_ms
                )
                if result == 1:
                    logger.debug(f"TTL do Lock estendido para {self.router_id}")
                else:
                    logger.error(f"Perda do lock durante execução no roteador {self.router_id}!")
                    self._is_held = False
                    break
        except asyncio.CancelledError:
            pass

    async def release(self):
        """Libera o lock de forma atômica e segura."""
        self._is_held = False
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()

        try:
            result = await self.redis.eval(
                LUA_RELEASE_LOCK, 1, self.lock_key, self.token
            )
            if result == 1:
                logger.info(f"Lock liberado com sucesso para {self.router_id}")
            else:
                logger.warning(f"Lock expirou ou pertencia a outro processo para {self.router_id}")
        except Exception as e:
            logger.error(f"Erro ao liberar lock: {e}")
