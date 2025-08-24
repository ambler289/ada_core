# ada_ui_bootstrap.py
# v1.0 — shared, reloadable bootstrap for ADa UI

from __future__ import annotations
import os, sys, importlib, types
from typing import Optional, Tuple

__all__ = ["ensure_ada_ui_path", "get_forms", "reload_ada_ui", "__version__"]
__version__ = "1.0"

def _candidate_paths(script_dir: Optional[str] = None):
    """Yield best-guess locations for ada_ui."""
    env = os.getenv("ADA_UI_DIR")
    if env:
        yield env

    appdata = os.getenv("APPDATA")  # C:\Users\<you>\AppData\Roaming
    if appdata:
        yield os.path.join(appdata, "pyRevit", "Extensions", "ADa-Manage.extension", "lib", "ada_ui")
        yield os.path.join(appdata, "pyRevit", "Extensions", "ADa-Tools.extension",  "lib", "ada_ui")

    # sibling lib/ada_ui if script is inside an extension tree
    if script_dir:
        yield os.path.normpath(os.path.join(script_dir, "..", "..", "lib", "ada_ui"))
        yield os.path.normpath(os.path.join(script_dir, "..", "lib", "ada_ui"))

def ensure_ada_ui_path(script_file: Optional[str] = None) -> Optional[str]:
    """
    Ensure ada_ui directory is on sys.path. Returns the path used (or None).
    Call this once near the top of each script.
    """
    here = os.path.dirname(script_file) if script_file else None
    for p in _candidate_paths(here):
        if p and os.path.isdir(p):
            if p not in sys.path:
                sys.path.insert(0, p)
            return p
    return None

def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

def get_forms(prefer: str = "ada_brandforms_v6") -> Tuple[types.ModuleType, str]:
    """
    Import a 'forms' provider with sensible fallbacks.
    Returns (forms_module, source_name).
      prefer: "ada_brandforms_v6" (default) or "ada_bootstrap"
    """
    # Preferred theme
    if prefer == "ada_brandforms_v6":
        mod = _try_import("ada_brandforms_v6")
        if mod and hasattr(mod, "forms"):
            return mod.forms, "ada_brandforms_v6"
        # Some themes expose top-level API directly
        if mod and hasattr(mod, "alert"):
            return mod, "ada_brandforms_v6"
    elif prefer == "ada_bootstrap":
        mod = _try_import("ada_bootstrap")
        if mod and hasattr(mod, "forms"):
            return mod.forms, "ada_bootstrap"

    # Fallback to ada_bootstrap if available
    mod = _try_import("ada_bootstrap")
    if mod and hasattr(mod, "forms"):
        return mod.forms, "ada_bootstrap"

    # Last resort: pyRevit's forms
    pv = _try_import("pyrevit.forms")
    if pv:
        return pv, "pyrevit.forms"

    # If everything failed, raise a clear error
    raise ImportError("No suitable forms provider found (ada_brandforms_v6, ada_bootstrap, or pyrevit.forms).")

def reload_ada_ui(prefer: str = "ada_brandforms_v6") -> Tuple[types.ModuleType, str]:
    """
    Hard-reload ada_ui + themed UI modules so changes are picked up without restarting Revit.
    Returns (forms_module, source_name).
    """
    # Invalidate import caches
    importlib.invalidate_caches()

    # Wipe ada_ui and our themed modules from sys.modules
    victims = []
    for name in list(sys.modules.keys()):
        if name.startswith("ada_ui") or name in ("ada_brandforms_v6", "ada_bootstrap"):
            victims.append(name)
    for name in victims:
        try:
            del sys.modules[name]
        except Exception:
            pass

    # Re-import
    return get_forms(prefer=prefer)
