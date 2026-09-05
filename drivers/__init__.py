from core.models import RouterVendor
from drivers.base import BaseNetworkDriver
from drivers.mikrotik import MikroTikDriver
from drivers.cisco import CiscoDriver
from drivers.juniper import JuniperDriver
from drivers.huawei import HuaweiDriver


def get_driver(vendor: RouterVendor, host: str, port: int = 22, username: str = "", password: str = "") -> BaseNetworkDriver:
    if vendor == RouterVendor.MIKROTIK:
        return MikroTikDriver(host, port, username or "admin", password)
    elif vendor == RouterVendor.CISCO:
        return CiscoDriver(host, port, username or "cisco", password or "cisco")
    elif vendor == RouterVendor.JUNIPER:
        return JuniperDriver(host, port, username or "root", password or "Juniper")
    elif vendor == RouterVendor.HUAWEI:
        return HuaweiDriver(host, port, username or "huawei", password or "Huawei@123")
    raise ValueError(f"Fabricante não suportado: {vendor}")
