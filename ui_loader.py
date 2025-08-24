# ui_loader.py — minimal, deterministic loader for ADa UI (lib/ada_ui only)

import sys, importlib
from pathlib import Path

# 1) Put this extension's lib first on sys.path
def _extension_lib() -> Path | None:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if p.name.endswith(".extension"):
            lib = p / "lib"
            if lib.exists():
                if str(lib) in sys.path:
                    sys.path.remove(str(lib))
                sys.path.insert(0, str(lib))     # force-first
                return lib
    return None

LIB_DIR = _extension_lib()
ADA_UI_DIR = LIB_DIR / "ada_ui" if LIB_DIR else None

# 2) Nuke any previously-imported "ada_ui" that might be shadowing our submodule
for k in list(sys.modules.keys()):
    if k == "ada_ui" or k.startswith("ada_ui."):
        sys.modules.pop(k, None)

def _load_by_file(fname: str):
    """Load a module from lib/ada_ui/<fname> if present."""
    if not ADA_UI_DIR:
        return None, None
    path = ADA_UI_DIR / fname
    if not path.exists():
        return None, None
    try:
        spec = importlib.util.spec_from_file_location("ada_ui_" + path.stem, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod, str(path)
    except Exception:
        return None, None

def _resolve_alert():
    # v6 -> v5 -> v4_2 from lib/ada_ui/* only
    for fname in ("ada_brandforms_v6.py", "ada_brandforms_v5.py", "ada_brandforms_v4_2.py"):
        mod, src = _load_by_file(fname)
        if mod:
            if hasattr(mod, "alert"):
                return mod.alert, f"{src} (alert)"
            if hasattr(mod, "BrandForms"):
                return (lambda msg, title='Message': mod.BrandForms.alert(msg, title=title)), f"{src} (BrandForms.alert)"

    # bootstrap fallback from lib/ada_ui/ only
    mod, src = _load_by_file("ada_bootstrap.py")
    if mod and hasattr(mod, "forms") and hasattr(mod.forms, "alert"):
        return (lambda m, title='Message': mod.forms.alert(m, title=title)), f"{src} (bootstrap.forms)"

    # pyRevit fallback
    try:
        from pyrevit import forms as _pv
        return (lambda m, title="Message": _pv.alert(m, title=title)), "pyrevit.forms"
    except Exception:
        pass

    # OS message box (last resort)
    from System.Windows import MessageBox
    return (lambda m, title="Message": MessageBox.Show(str(m), str(title))), "System.Windows.MessageBox"

# Public API
ui_alert, __ui_source__ = _resolve_alert()

# Optional quick self-test (comment out when done)
# try: ui_alert(f"UI provider: {__ui_source__}", title="Preflight"); except: pass
