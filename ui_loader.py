# Minimal, deterministic ADa UI loader with unified helpers.
# Works with submodules; only uses files under .../.extension/lib/ada_ui/

from __future__ import annotations
import sys, importlib
from pathlib import Path
from typing import Any, Iterable, List

# ─────────────────────────────────────────────────────────────────────────────
# Locate this extension's lib/ and the ada_ui folder; force lib/ to the front
# ─────────────────────────────────────────────────────────────────────────────
def _extension_lib() -> Path | None:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if p.name.endswith(".extension"):
            lib = p / "lib"
            if lib.exists():
                if str(lib) in sys.path:
                    sys.path.remove(str(lib))
                sys.path.insert(0, str(lib))
                return lib
    return None

LIB_DIR = _extension_lib()
ADA_UI_DIR = LIB_DIR / "ada_ui" if LIB_DIR else None

# purge any previously-imported global "ada_ui" that could shadow our submodule
for k in list(sys.modules.keys()):
    if k == "ada_ui" or k.startswith("ada_ui."):
        sys.modules.pop(k, None)

def _load_file(fname: str):
    """Load a module directly from lib/ada_ui/<fname>."""
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

# ─────────────────────────────────────────────────────────────────────────────
# Resolve a provider (module) and adapt to uniform helpers
# ─────────────────────────────────────────────────────────────────────────────
_PROVIDERS = (
    "ada_brandforms_v6.py",
    "ada_brandforms_v5.py",
    "ada_brandforms_v4_2.py",
    "ada_brandforms_v4.py",
    "ada_brandforms_v3.py",
)

_provider_mod = None
__ui_source__ = "System.Windows.MessageBox"

# Try brandforms v6→v5→v4_2→v4→v3
for fname in _PROVIDERS:
    m, src = _load_file(fname)
    if not m:
        continue
    _provider_mod = m
    __ui_source__ = src
    break

# Fallback: ada_bootstrap.py
if _provider_mod is None:
    m, src = _load_file("ada_bootstrap.py")
    if m and hasattr(m, "forms"):
        _provider_mod = m
        __ui_source__ = f"{src} (bootstrap.forms)"

# Fallback: pyRevit forms
if _provider_mod is None:
    try:
        from pyrevit import forms as _pv  # type: ignore
        _provider_mod = _pv
        __ui_source__ = "pyrevit.forms"
    except Exception:
        _provider_mod = None

# ─────────────────────────────────────────────────────────────────────────────
# Unified helpers
# ─────────────────────────────────────────────────────────────────────────────
def ui_alert(msg: Any, title: str = "ADa") -> None:
    """Show info/OK dialog."""
    if _provider_mod is None:
        from System.Windows import MessageBox
        MessageBox.Show(str(msg), str(title))
        return

    # brandforms v6/v5: function alert()
    if hasattr(_provider_mod, "alert"):
        _provider_mod.alert(msg, title=title)  # type: ignore
        return
    # brandforms v4.x/v3: class BrandForms.alert()
    if hasattr(_provider_mod, "BrandForms"):
        _provider_mod.BrandForms.alert(msg, title=title)  # type: ignore
        return
    # ada_bootstrap.forms
    if hasattr(_provider_mod, "forms"):
        _provider_mod.forms.alert(msg, title=title)  # type: ignore
        return
    # pyRevit forms
    if hasattr(_provider_mod, "alert"):
        _provider_mod.alert(msg, title=title)  # type: ignore
        return

    from System.Windows import MessageBox
    MessageBox.Show(str(msg), str(title))

def ui_confirm(msg: Any, title: str = "Confirm", yes_text: str = "OK", no_text: str = "Cancel") -> bool:
    """Yes/No confirmation; returns True for Yes/OK."""
    if _provider_mod is None:
        from System.Windows import MessageBox, MessageBoxButton, MessageBoxResult
        return MessageBox.Show(str(msg), str(title), MessageBoxButton.OKCancel) == MessageBoxResult.OK

    # v6/v5 expose ask_yes_no / confirm / or BrandForms.alert(yes/no)
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
    """Prompt for a single line of text; returns string or None if cancelled."""
    if _provider_mod is None:
        # minimal WinForms input as a last resort
        try:
            import System.Windows.Forms as WinForms
            f = WinForms.Form()
            f.Text = str(title)
            f.Width, f.Height = 420, 150
            tb = WinForms.TextBox()
            tb.Text = str(default_text or "")
            tb.Width = 360; tb.Left = 20; tb.Top = 35
            lb = WinForms.Label(); lb.Text = str(prompt); lb.Left = 20; lb.Top = 12; lb.Width = 360
            ok = WinForms.Button(); ok.Text = "OK"; ok.Left = 220; ok.Top = 70; ok.DialogResult = WinForms.DialogResult.OK
            cancel = WinForms.Button(); cancel.Text = "Cancel"; cancel.Left = 300; cancel.Top = 70; cancel.DialogResult = WinForms.DialogResult.Cancel
            f.Controls.Add(lb); f.Controls.Add(tb); f.Controls.Add(ok); f.Controls.Add(cancel)
            f.AcceptButton = ok; f.CancelButton = cancel
            return tb.Text if f.ShowDialog() == WinForms.DialogResult.OK else None
        except Exception:
            return default_text or None

    # brandforms v6/v5: input_box(title, label/prompt, default_text)
    if hasattr(_provider_mod, "input_box"):
        try:
            return _provider_mod.input_box(title=title, label=prompt, default_text=default_text)  # type: ignore
        except TypeError:
            # some variants use (title, prompt, default_text)
            return _provider_mod.input_box(title, prompt, default_text)  # type: ignore

    # v4.x/v3: BrandForms.ask_for_string
    if hasattr(_provider_mod, "BrandForms"):
        return _provider_mod.BrandForms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore

    # ada_bootstrap.forms
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "ask_for_string"):
        return _provider_mod.forms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore

    # pyRevit (may not work under CPython, but harmless to try)
    if hasattr(_provider_mod, "ask_for_string"):
        return _provider_mod.ask_for_string(default=default_text)  # type: ignore

    return default_text or None

def ui_select(title: str, items: Iterable[Any], message: str | None = None, multi: bool = False):
    """Select from a list. Returns selected item(s) or None."""
    items = list(items)

    if _provider_mod is None:
        # very small WinForms list fallback
        try:
            import System.Windows.Forms as WinForms
            f = WinForms.Form(); f.Text = str(title); f.Width, f.Height = 420, 300
            lb = WinForms.Label(); lb.Text = str(message or ""); lb.Left = 12; lb.Top = 8; lb.Width = 380
            lst = WinForms.ListBox(); lst.Left = 12; lst.Top = 28; lst.Width = 380; lst.Height = 200
            if multi:
                lst.SelectionMode = WinForms.SelectionMode.MultiExtended
            for it in items: lst.Items.Add(it)
            ok = WinForms.Button(); ok.Text = "OK"; ok.Left = 230; ok.Top = 240; ok.DialogResult = WinForms.DialogResult.OK
            cancel = WinForms.Button(); cancel.Text = "Cancel"; cancel.Left = 312; cancel.Top = 240; cancel.DialogResult = WinForms.DialogResult.Cancel
            f.Controls.Add(lb); f.Controls.Add(lst); f.Controls.Add(ok); f.Controls.Add(cancel)
            f.AcceptButton = ok; f.CancelButton = cancel
            dlg = f.ShowDialog()
            if dlg != WinForms.DialogResult.OK:
                return None
            if multi:
                return [lst.Items[i] for i in lst.SelectedIndices]
            return lst.SelectedItem
        except Exception:
            return items if (multi and items) else (items[0] if items else None)

    # brandforms rarely include a list picker; try ada_bootstrap helper if available
    # (many ADa repos ship a helper _wf_select_from_list on ada_bootstrap)
    try:
        m_boot, _ = _load_file("ada_bootstrap.py")
        if m_boot and hasattr(m_boot, "_wf_select_from_list"):
            sfl = m_boot._wf_select_from_list()
            return sfl.show(items, title=title, multi=multi)  # type: ignore
    except Exception:
        pass

    # fallbacks: show a message + return first/None
    ui_alert(message or "Select item(s) then press OK.", title=title)
    return items if (multi and items) else (items[0] if items else None)
