import importlib
import os

ENUM_MODULES = {}

def load_enum_modules():
    path = os.path.dirname(__file__)
    for f in os.listdir(path):
        if f.endswith(".py") and f != "__init__.py":
            name = f[:-3]
            ENUM_MODULES[name] = f"seerAD.enum.{name}"

def get_enum_module(name):
    mod_path = ENUM_MODULES.get(name)
    if not mod_path:
        raise ValueError(f"Unknown module: {name}")
    mod = importlib.import_module(mod_path)
    if not hasattr(mod, "run"):
        raise ValueError(f"Module '{name}' does not define a run(method, args) function.")
    return mod.run