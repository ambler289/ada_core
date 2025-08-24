# lib/ada_core/ui_loader.py
# Unified ADa UI loader (works with lib/ submodules & nested folders)

import sys, importlib, fnmatch
from pathlib import Path

def _find_extension_lib() -> Path | None:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if p.name.endswith(".extension"):
            lib = p / "lib"
            if lib.exists():
                if str(lib) not in sys.path:
                    sys.path.insert(0, str(lib))
                return lib
    return None

LIB_DIR = _find_extension_lib()

def _iter_candidates(patterns: list[str]):
    """Yield paths under lib/ that match any of the patterns (recursive)."""
    if not LIB_DIR:
        return
    for path in LIB_DIR.rglob("*.py"):
        name = path.name
        if any(fnmatch.fnmatch(name, pat) for pat in patterns):
            yield path

def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location("ada_dyn." + path.stem, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod

def _resolve_alert():
    # 1) Prefer brandforms v6 -> v5 -> v4_2 by filename, anywhere under lib/
    for pattern, tag in (("ada_brandforms_v6.py", "v6"),
                         ("ada_brandforms_v5.py", "v5"),
                         ("ada_brandforms_v4_2.py", "v4_2")):
        for p in _iter_candidates([pattern]):
            try:
                m = _load_module_from_path(p)
                if hasattr(m, "alert"):
                    return m.alert, f"{p} (alert)"
                if hasattr(m, "BrandForms"):
                    return (lambda msg, title='Message': m.BrandForms.alert(msg, title=title)), f"{p} (BrandForms.alert)"
            except Exception:
                continue

    # 2) Fallback to ada_bootstrap.forms (anywhere under lib/)
    for p in _iter_candidates(["ada_bootstrap.py"]):
        try:
            m = _load_module_from_path(p)
            if hasattr(m, "forms") and hasattr(m.forms, "alert"):
                return (lambda msg, title='Message': m.forms.alert(msg, title=title)), f"{p} (bootstrap.forms)"
        except Exception:
            continue

    # 3) pyRevit fallback
    try:
        from pyrevit import forms as _pv
        return (lambda m, title="Message": _pv.alert(m, title=title)), "pyrevit.forms"
    except Exception:
        pass

    # 4) Last resort
    from System.Windows import MessageBox
    return (lambda m, title="Message": MessageBox.Show(str(m), str(title))), "System.Windows.MessageBox"

# Public API
ui_alert, __ui_source__ = _resolve_alert()
