# ui_loader.py
# Centralised loader for ADa UI theming
# Usage: from ada_core.ui_loader import ui_alert, __ui_source__

import sys, importlib
from pathlib import Path

def _add_extension_lib():
    """Ensure .../.extension/lib is on sys.path."""
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if p.name.endswith(".extension"):
            lib = p / "lib"
            if lib.exists() and str(lib) not in sys.path:
                sys.path.insert(0, str(lib))
            return lib
    return None

LIB_DIR = _add_extension_lib()

def _ensure_ada_ui_package() -> bool:
    """Make ada_ui a package if missing __init__.py."""
    try:
        import ada_ui  # noqa
        return True
    except Exception:
        if not LIB_DIR:
            return False
        pkg = LIB_DIR / "ada_ui"
        if not pkg.exists():
            return False
        init_py = pkg / "__init__.py"
        if not init_py.exists():
            try:
                init_py.write_text("# auto-init\n", encoding="utf-8")
            except Exception:
                pass
        try:
            import ada_ui  # noqa
            return True
        except Exception:
            return False

_ensure_ada_ui_package()

def _load_brandforms():
    """Resolve alert() function and identify provider."""
    # 1. Normal imports
    for modname in (
        "ada_ui.ada_brandforms_v6",
        "ada_ui.ada_brandforms_v5",
        "ada_ui.ada_brandforms_v4_2",
    ):
        try:
            m = importlib.import_module(modname)
            if hasattr(m, "alert"):
                return m.alert, modname + " (alert)"
            if hasattr(m, "BrandForms"):
                return (
                    lambda msg, title="Message": m.BrandForms.alert(msg, title=title),
                    modname + " (BrandForms.alert)",
                )
        except Exception:
            pass

    # 2. Direct file load
    if LIB_DIR:
        for filename, tag in (
            ("ada_brandforms_v6.py", "v6"),
            ("ada_brandforms_v5.py", "v5"),
            ("ada_brandforms_v4_2.py", "v4_2"),
        ):
            path = LIB_DIR / "ada_ui" / filename
            if path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(
                        "ada_ui." + path.stem, str(path)
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore
                    if hasattr(mod, "alert"):
                        return mod.alert, f"file:{filename} (alert)"
                    if hasattr(mod, "BrandForms"):
                        return (
                            lambda msg, title="Message": mod.BrandForms.alert(
                                msg, title=title
                            ),
                            f"file:{filename} (BrandForms.alert)",
                        )
                except Exception:
                    pass

    # 3. ada_bootstrap fallback
    try:
        from ada_ui.ada_bootstrap import forms as _bf
        return (lambda m, title="Message": _bf.alert(m, title=title)), "ada_ui.ada_bootstrap.forms"
    except Exception:
        pass

    # 4. pyRevit fallback
    try:
        from pyrevit import forms as _pv
        return (lambda m, title="Message": _pv.alert(m, title=title)), "pyrevit.forms"
    except Exception:
        pass

    # 5. Last resort OS MessageBox
    from System.Windows import MessageBox
    return (lambda m, title="Message": MessageBox.Show(str(m), str(title))), "System.Windows.MessageBox"

# Expose
ui_alert, __ui_source__ = _load_brandforms()
