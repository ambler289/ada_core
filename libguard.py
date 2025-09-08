# ada_core/libguard.py
# Deterministic third-party bootstrap for pyRevit CPython3 tools.
# - Adds ADa thirdparty/UI paths FIRST
# - Neutralizes PYTHONPATH + user site
# - Optionally strips foreign site-packages
# - Optional NumPy/Shapely verification + quick diagnostics

from __future__ import annotations
import os, sys, re, typing as _t

# Patterns that often inject stray packages ahead of our wheels
_BLOCK_PATTERNS = (
    r"\\Users\\[^\\]+\\AppData\\Local\\Programs\\Python\\Python\d+\\Lib\\site-packages",
    r"\\Program Files( \(x86\))?\\Python\\Python\d+\\Lib\\site-packages",
)
# Keep anything inside our managed extension trees
_AD_MARKERS = (
    "\\ADa-Tools.extension\\lib\\thirdparty\\",
    "\\ADa-Manage.extension\\lib\\thirdparty\\",
)

def _find_ext_root(start_path: str) -> str | None:
    p = os.path.abspath(start_path)
    while True:
        for marker in ("ADa-Tools.extension", "ADa-Manage.extension"):
            if p.lower().endswith(marker.lower()):
                return p
            idx = p.lower().rfind("\\" + marker.lower() + "\\")
            if idx != -1:
                return p[:idx + len("\\" + marker)]
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent

def _prepend(path: str) -> None:
    if path and os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

def ensure_thirdparty(
    caller_file: str | None = None,
    strict_sanitize: bool = True,
    add_ui: bool = True,
    add_common: bool = True,
    add_bin: bool = True,
) -> dict:
    """
    Make third-party imports deterministic for pyRevit CPython3.
    Returns a dict with resolved paths for logging/inspection.

    - `caller_file`: usually __file__ from the calling script.
    - `strict_sanitize`: remove foreign site-packages from sys.path.
    - `add_ui/common/bin`: control which ADa paths are inserted.
    """
    # 0) Tame ambient env in this Revit process
    os.environ.pop("PYTHONPATH", None)              # ignore global overlays
    os.environ.setdefault("PYTHONNOUSERSITE", "1")  # ignore user site-packages

    # 1) Resolve extension root (from caller or default roaming path)
    ext_root = None
    if caller_file:
        ext_root = _find_ext_root(caller_file)
    if not ext_root:
        ext_root = os.path.expandvars(r"%APPDATA%\pyRevit\Extensions\ADa-Tools.extension")

    # 2) Build our important paths
    tp_root = os.path.join(ext_root, "lib", "thirdparty")
    tp_bin  = os.environ.get("ADA_THIRDPARTY_DIR") or os.path.join(tp_root, "win-amd64-cp312")
    tp_com  = os.path.join(tp_root, "common")
    ada_ui  = os.environ.get("ADA_UI_DIR") or os.path.join(ext_root, "lib", "ada_ui")

    # 3) Prepend them so our wheels win
    if add_ui:    _prepend(ada_ui)
    if add_common:_prepend(tp_com)
    if add_bin:   _prepend(tp_bin)

    # 4) Optionally call legacy bootstrap if present (no-op if missing)
    try:
        from ada_bootstrap import ensure_paths  # type: ignore
        ensure_paths(strict=False)
    except Exception:
        pass

    # 5) Sanitize foreign site-packages (but keep anything inside our extensions)
    if strict_sanitize:
        clean = []
        for p in sys.path:
            low = p.lower()
            bad = any(re.search(bp, p, flags=re.IGNORECASE) for bp in _BLOCK_PATTERNS)
            if bad and not any(m.lower() in low for m in _AD_MARKERS):
                continue
            clean.append(p)
        sys.path[:] = clean

    return {"ext_root": ext_root, "tp_bin": tp_bin, "tp_common": tp_com, "ada_ui": ada_ui}

def verify_numpy_shapely(expected_fragment: str = "\\lib\\thirdparty\\win-amd64-cp312\\") -> tuple[str, str, str]:
    """
    Import NumPy & Shapely and assert they’re loading from our bundled wheels.
    Raises RuntimeError with a clear message if not.
    Returns (numpy_version, numpy_path, geos_version_string).
    """
    import numpy as _np
    from shapely import geos as _geos
    np_p   = getattr(_np, "__file__", "") or ""
    geos_p = getattr(_geos, "__file__", "") or ""
    if expected_fragment.lower() not in np_p.lower() or expected_fragment.lower() not in geos_p.lower():
        raise RuntimeError(
            "NumPy/Shapely are not loading from ADa thirdparty.\n"
            f"NumPy: {np_p}\nGEOS:  {geos_p}\n"
            "Ensure CPython3 engine and that libguard.ensure_thirdparty() ran before imports."
        )
    return (_np.__version__, np_p, _geos.geos_version_string)

def print_numpy_shapely(out: _t.Any = None) -> None:
    """
    Convenience: print the active NumPy + GEOS locations to pyRevit output (or stdout fallback).
    """
    try:
        import numpy as _np
        from shapely import geos as _geos
        line1 = f"**NumPy** {_np.__version__}\n`{getattr(_np,'__file__','?')}`"
        line2 = f"**GEOS**  {_geos.geos_version_string}\n`{getattr(_geos,'__file__','?')}`"
        if out is None:
            from pyrevit import script as _script  # type: ignore
            out = _script.get_output()
        out.print_md(line1); out.print_md(""); out.print_md(line2)
    except Exception as e:
        msg = f"[libguard] Failed to print NumPy/GEOS info: {e}"
        try:
            if out is None:
                from pyrevit import script as _script  # type: ignore
                out = _script.get_output()
            out.print_md(msg)
        except Exception:
            print(msg)