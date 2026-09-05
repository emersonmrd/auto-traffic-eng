from abc import ABC, abstractmethod
from typing import Dict, Any
from core.models import ActionType
import logging

logger = logging.getLogger("BaseDriver")


class BaseNetworkDriver(ABC):
    """
    Interface base obrigatória para drivers de roteadores de borda.
    Garante o fluxo de validação Closed-Loop e Dead Man's Switch (Rollback Seguro).
    """

    def __init__(self, host: str, port: int, username: str, password: str = ""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    @abstractmethod
    async def connect(self):
        """Estabelece conexão segura com o roteador (SSH / Scrapli / Netmiko)."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Encerra a conexão com o roteador."""
        pass

    @abstractmethod
    async def pre_check_baseline(self) -> Dict[str, Any]:
        """
        Coleta o estado basal antes da mudança:
        - Sessões BGP (Established)
        - Rotas anunciadas / recebidas
        - Contadores de tráfego de interface (se disponível)
        """
        pass

    @abstractmethod
    async def apply_traffic_shift(self, action: ActionType, safe_timer_seconds: int = 180):
        """
        Aplica a manipulação de tráfego armando o Dead Man's Switch (ex: commit confirmed).
        Se o script morrer aqui, o roteador deve reverter sozinho após safe_timer_seconds.
        """
        pass

    @abstractmethod
    async def post_check_telemetry(self, baseline: Dict[str, Any]) -> bool:
        """
        Valida se o tráfego e os anúncios BGP realmente convergiram para o alvo desejado.
        Retorna True se bem-sucedido, False se falhou.
        """
        pass

    @abstractmethod
    async def confirm_commit(self):
        """
        Confirma a alteração de forma definitiva (ex: 'commit' final ou remoção do scheduler de rollback).
        """
        pass

    @abstractmethod
    async def rollback(self):
        """Reverte imediatamente para a configuração original."""
        pass
