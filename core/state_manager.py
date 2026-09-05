from core.models import NetworkState, ActionType
from typing import Tuple


class FSMValidationError(Exception):
    pass


class NetworkFSM:
    """
    Controlador de Máquina de Estados Finita (FSM) para manipulação de tráfego.
    Garante que ações ilegais não sejam disparadas.
    """

    VALID_TRANSITIONS = {
        NetworkState.NORMAL_DEFAULT: [ActionType.SHUNT_TO_OP1, ActionType.SHUNT_TO_OP2],
        NetworkState.SHUNTED_OP1: [ActionType.ROLLBACK_DEFAULT],
        NetworkState.SHUNTED_OP2: [ActionType.ROLLBACK_DEFAULT],
        NetworkState.FAILED_DIRTY: [],  # Requer reconciliação manual
    }

    @classmethod
    def validate_transition(cls, current_state: NetworkState, requested_action: ActionType) -> bool:
        allowed_actions = cls.VALID_TRANSITIONS.get(current_state, [])
        if requested_action not in allowed_actions:
            raise FSMValidationError(
                f"Transição inválida: Não é permitido executar '{requested_action.value}' "
                f"quando a rede está no estado '{current_state.value}'."
            )
        return True

    @classmethod
    def get_target_state(cls, action: ActionType) -> NetworkState:
        if action == ActionType.SHUNT_TO_OP1:
            return NetworkState.SHUNTED_OP1
        elif action == ActionType.SHUNT_TO_OP2:
            return NetworkState.SHUNTED_OP2
        elif action == ActionType.ROLLBACK_DEFAULT:
            return NetworkState.NORMAL_DEFAULT
        return NetworkState.FAILED_DIRTY
