
# ada_core package (lazy, 2026-safe)
# Avoid eager imports so a failure in any submodule doesn't blow up __init__ at line 3.
# Provides lazy attribute loading via PEP 562 (__getattr__).

from importlib import import_module
from types import ModuleType
from typing import Dict

__all__ = [
    "selection","ui","units","views","collect","gp","params",
    "geom","naming","config","log","errors","deps","viewsheets"
]

_cache: Dict[str, ModuleType] = {}

def __getattr__(name: str) -> ModuleType:
    if name in __all__:
        mod = _cache.get(name)
        if mod is not None:
            return mod
        try:
            mod = import_module(f".{name}", __name__)
        except Exception as e:
            # Raise a clearer error that identifies the *actual* failing submodule.
            raise ImportError(f"ada_core: failed to import submodule '{name}': {e}") from e
        _cache[name] = mod
        return mod
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Optional convenience: allow 'import ada_core.gp as gp' to work
# by exposing submodules as attributes in package namespace when loaded.
def __dir__():
    return sorted(list(globals().keys()) + __all__)
