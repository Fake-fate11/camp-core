from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BendersCut",
    "BendersMaster",
    "BendersMasterConfig",
    "BendersMasterSolution",
    "ParametricTorchMaster",
    "ParametricTorchMasterConfig",
]

_EXPORT_MODULES = {
    "BendersCut": ".benders_master",
    "BendersMaster": ".benders_master",
    "BendersMasterConfig": ".benders_master",
    "BendersMasterSolution": ".benders_master",
    "ParametricTorchMaster": ".parametric_torch_master",
    "ParametricTorchMasterConfig": ".parametric_torch_master",
}


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value
