from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class RouterVendor(str, Enum):
    MIKROTIK = "mikrotik"
    CISCO = "cisco"
    JUNIPER = "juniper"
    HUAWEI = "huawei"


class NetworkState(str, Enum):
    NORMAL_DEFAULT = "NORMAL_DEFAULT"
    SHUNT_PENDING = "SHUNT_PENDING"
    SHUNTED_OP1 = "SHUNTED_OP1"
    SHUNTED_OP2 = "SHUNTED_OP2"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    FAILED_DIRTY = "FAILED_DIRTY"


class ActionType(str, Enum):
    SHUNT_TO_OP1 = "SHUNT_TO_OP1"
    SHUNT_TO_OP2 = "SHUNT_TO_OP2"
    ROLLBACK_DEFAULT = "ROLLBACK_DEFAULT"


class JobStatus(str, Enum):
    ENQUEUED = "ENQUEUED"
    ACQUIRING_LOCK = "ACQUIRING_LOCK"
    PRE_CHECK = "PRE_CHECK"
    APPLYING_SAFE_COMMIT = "APPLYING_SAFE_COMMIT"
    WAITING_CONVERGENCE = "WAITING_CONVERGENCE"
    POST_CHECK_TELEMETRY = "POST_CHECK_TELEMETRY"
    CONFIRMING_COMMIT = "CONFIRMING_COMMIT"
    COMPLETED = "COMPLETED"
    FAILED_ROLLED_BACK = "FAILED_ROLLED_BACK"
    DEADLOCK_ABORTED = "DEADLOCK_ABORTED"


class TrafficJob(BaseModel):
    job_id: str
    action: ActionType
    vendor: RouterVendor
    target_router_ip: str
    target_router_port: int = 22
    username: str
    password: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    requested_by_user_id: int
    requested_by_username: Optional[str] = None
    status: JobStatus = JobStatus.ENQUEUED
    details: Dict[str, Any] = Field(default_factory=dict)
