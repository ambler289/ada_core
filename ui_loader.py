# lib/ada_core/ui_loader.py
# Deterministic ADa UI loader (submodule-safe) with diagnostics.

from __future__ import annotations
import sys, importlib, traceback
from pathlib import Path
from typing import Any, Iterable

__ui_source__ = "System.Windows.MessageBox"
__ui_debug__  = []   # step-by-step trace of what we tried/loaded

def _log(msg: str):
    __ui_debug__.append(msg)

# 1) Put this extension's lib first on sys.path
def _extension_lib() -> Path | None:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if p.name.endswith(".extension"):
            lib = p / "lib"
            if lib.exists():
                if str(lib) in sys.path:
                    sys.path.remove(str(lib))
                sys.path.insert(0, str(lib))
                _log(f"lib = {lib}")
                return lib
    _log("lib NOT found")
    return None

LIB_DIR = _extension_lib()
ADA_UI_DIR = LIB_DIR / "ada_ui" if LIB_DIR else None
_log(f"ada_ui dir = {ADA_UI_DIR if ADA_UI_DIR else 'None'}")

# 2) Clear any previously-imported global ada_ui to avoid shadowing
for k in list(sys.modules.keys()):
    if k == "ada_ui" or k.startswith("ada_ui."):
        sys.modules.pop(k, None)
        _log(f"purged module: {k}")

def _load_file(fname: str):
    """Load a module directly by filename under lib/ada_ui/."""
    if not ADA_UI_DIR:
        _log("ADA_UI_DIR missing")
        return None, None
    path = ADA_UI_DIR / fname
    if not path.exists():
        _log(f"missing: {path}")
        return None, None
    try:
        _log(f"loading: {path}")
        spec = importlib.util.spec_from_file_location("ada_ui_" + path.stem, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        _log(f"loaded: {path}")
        return mod, str(path)
    except Exception:
        _log(f"EXC loading {path}:\n{traceback.format_exc()}")
        return None, None

# 3) Resolve provider
_PROVIDER_FILES = (
    "ada_brandforms_v6.py",
    "ada_brandforms_v5.py",
    "ada_brandforms_v4_2.py",
    "ada_brandforms_v4.py",
    "ada_brandforms_v3.py",
)

_provider_mod = None

for fname in _PROVIDER_FILES:
    m, src = _load_file(fname)
    if not m:
        continue
    _provider_mod = m
    __ui_source__ = src
    break

# Fallback: ada_bootstrap
if _provider_mod is None:
    m, src = _load_file("ada_bootstrap.py")
    if m and hasattr(m, "forms"):
        _provider_mod = m
        __ui_source__ = f"{src} (bootstrap.forms)"

# Fallback: pyRevit
if _provider_mod is None:
    try:
        from pyrevit import forms as _pv  # type: ignore
        _provider_mod = _pv
        __ui_source__ = "pyrevit.forms"
        _log("using pyrevit.forms")
    except Exception:
        _log("pyrevit.forms not available")

# 4) Unified helpers
def ui_alert(msg: Any, title: str = "ADa") -> None:
    if _provider_mod is None:
        from System.Windows import MessageBox
        MessageBox.Show(str(msg), str(title))
        return
    # brandforms v6/v5
    if hasattr(_provider_mod, "alert"):
        _provider_mod.alert(msg, title=title)  # type: ignore
        return
    # v4.x/v3
    if hasattr(_provider_mod, "BrandForms"):
        _provider_mod.BrandForms.alert(msg, title=title)  # type: ignore
        return
    # bootstrap
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "alert"):
        _provider_mod.forms.alert(msg, title=title)  # type: ignore
        return
    # pyrevit fallback
    if hasattr(_provider_mod, "alert"):
        _provider_mod.alert(msg, title=title)  # type: ignore
        return
    from System.Windows import MessageBox
    MessageBox.Show(str(msg), str(title))

def ui_confirm(msg: Any, title: str = "Confirm") -> bool:
    if _provider_mod is None:
        from System.Windows import MessageBox, MessageBoxButton, MessageBoxResult
        return MessageBox.Show(str(msg), str(title), MessageBoxButton.OKCancel) == MessageBoxResult.OK
    for name in ("ask_yes_no", "confirm"):
        if hasattr(_provider_mod, name):
            return bool(getattr(_provider_mod, name)(msg, title=title))  # type: ignore
    if hasattr(_provider_mod, "BrandForms"):
        try:
            return bool(_provider_mod.BrandForms.alert(msg, title=title, yes=True, no=True))  # type: ignore
        except Exception:
            pass
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "confirm"):
        return bool(_provider_mod.forms.confirm(msg, title=title))  # type: ignore
    if hasattr(_provider_mod, "alert"):
        try:
            return bool(_provider_mod.alert(msg, title=title, yes=True, no=True))  # type: ignore
        except Exception:
            pass
    from System.Windows import MessageBox, MessageBoxButton, MessageBoxResult
    return MessageBox.Show(str(msg), str(title), MessageBoxButton.OKCancel) == MessageBoxResult.OK

def ui_input(title: str, prompt: str, default_text: str = "") -> str | None:
    if _provider_mod is None:
        try:
            import System.Windows.Forms as WF
            f = WF.Form(); f.Text = str(title); f.Width, f.Height = 420, 150
            tb = WF.TextBox(); tb.Text = str(default_text); tb.Width = 360; tb.Left = 20; tb.Top = 35
            lb = WF.Label(); lb.Text = str(prompt); lb.Left = 20; lb.Top = 12; lb.Width = 360
            ok = WF.Button(); ok.Text = "OK"; ok.Left = 220; ok.Top = 70; ok.DialogResult = WF.DialogResult.OK
            cancel = WF.Button(); cancel.Text = "Cancel"; cancel.Left = 300; cancel.Top = 70; cancel.DialogResult = WF.DialogResult.Cancel
            f.Controls.Add(lb); f.Controls.Add(tb); f.Controls.Add(ok); f.Controls.Add(cancel)
            f.AcceptButton = ok; f.CancelButton = cancel
            return tb.Text if f.ShowDialog() == WF.DialogResult.OK else None
        except Exception:
            return default_text or None
    if hasattr(_provider_mod, "input_box"):
        try:
            return _provider_mod.input_box(title=title, label=prompt, default_text=default_text)  # type: ignore
        except TypeError:
            return _provider_mod.input_box(title, prompt, default_text)  # type: ignore
    if hasattr(_provider_mod, "BrandForms"):
        return _provider_mod.BrandForms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "ask_for_string"):
        return _provider_mod.forms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore
    if hasattr(_provider_mod, "ask_for_string"):
        return _provider_mod.ask_for_string(default=default_text)  # type: ignore
    return default_text or None

def ui_select(title: str, items: Iterable[Any], message: str | None = None, multi: bool = False):
    items = list(items)
    # Try ada_bootstrap helper if present (many ADa repos ship this)
    m_boot, src = _load_file("ada_bootstrap.py")
    if m_boot and hasattr(m_boot, "_wf_select_from_list"):
        try:
            sfl = m_boot._wf_select_from_list()
            return sfl.show(items, title=title, multi=multi)  # type: ignore
        except Exception:
            pass
    # Minimal fallback
    ui_alert(message or "Select item(s) then press OK.", title=title)
    return items if (multi and items) else (items[0] if items else None)
