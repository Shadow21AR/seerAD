import importlib
import pkgutil
from typing import Dict, Callable

ENUM_MODULES: Dict[str, Callable] = {}

def load_enum_modules():
    global ENUM_MODULES
    ENUM_MODULES = {}
    for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{__name__}.{module_name}")
        if hasattr(mod, "run"):
            ENUM_MODULES[module_name] = mod.run

def get_enum_module(name: str) -> Callable:
    if name not in ENUM_MODULES:
        raise ValueError(f"Enumeration module '{name}' not found.")
    return ENUM_MODULES[name]
