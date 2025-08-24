# ADa UI loader (production): themed helpers with deterministic provider resolution.
# Looks only under .../.extension/lib/ada_ui/ and falls back cleanly.

from __future__ import annotations
import sys
import importlib
import importlib.util  # CPython in Revit needs this explicitly
from pathlib import Path
from typing import Any, Iterable

__ui_source__ = "System.Windows.MessageBox"

# ── locate this extension's lib/ and the ada_ui folder; force lib/ to front ──
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

LIB_DIR   = _extension_lib()
ADA_UI_DIR = LIB_DIR / "ada_ui" if LIB_DIR else None

# purge any preloaded global ada_ui modules that might shadow the submodule
for k in list(sys.modules.keys()):
    if k == "ada_ui" or k.startswith("ada_ui."):
        sys.modules.pop(k, None)

def _load_file(fname: str):
    """Load module directly from lib/ada_ui/<fname>; return (module, path_str) or (None, None)."""
    if not ADA_UI_DIR:
        return None, None
    path = ADA_UI_DIR / fname
    if not path.exists():
        return None, None
    try:
        spec = importlib.util.spec_from_file_location("ada_ui_" + path.stem, str(path))
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod, str(path)
    except Exception:
        return None, None

# ── resolve provider: v6 → v5 → v4_2 → v4 → v3 → bootstrap → pyRevit → MessageBox ──
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
    if m:
        _provider_mod = m
        __ui_source__ = src
        break

if _provider_mod is None:
    m, src = _load_file("ada_bootstrap.py")
    if m and hasattr(m, "forms"):
        _provider_mod = m
        __ui_source__ = f"{src} (bootstrap.forms)"

if _provider_mod is None:
    try:
        from pyrevit import forms as _pv  # type: ignore
        _provider_mod = _pv
        __ui_source__ = "pyrevit.forms"
    except Exception:
        _provider_mod = None  # final fallback handled in helpers

# ── unified helpers ──────────────────────────────────────────────────────────
def ui_alert(msg: Any, title: str = "ADa") -> None:
    if _provider_mod is None:
        from System.Windows import MessageBox
        MessageBox.Show(str(msg), str(title))
        return
    if hasattr(_provider_mod, "alert"):  # v6/v5 or pyRevit
        _provider_mod.alert(msg, title=title)  # type: ignore
        return
    if hasattr(_provider_mod, "BrandForms"):  # v4/v3
        _provider_mod.BrandForms.alert(msg, title=title)  # type: ignore
        return
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "alert"):  # bootstrap
        _provider_mod.forms.alert(msg, title=title)  # type: ignore
        return
    from System.Windows import MessageBox
    MessageBox.Show(str(msg), str(title))

def ui_confirm(msg: Any, title: str = "Confirm") -> bool:
    if _provider_mod is None:
        from System.Windows import MessageBox, MessageBoxButton, MessageBoxResult
        return MessageBox.Show(str(msg), str(title), MessageBoxButton.OKCancel) == MessageBoxResult.OK
    for name in ("ask_yes_no", "confirm"):  # v6/v5 variants
        if hasattr(_provider_mod, name):
            return bool(getattr(_provider_mod, name)(msg, title=title))  # type: ignore
    if hasattr(_provider_mod, "BrandForms"):  # v4/v3
        try:
            return bool(_provider_mod.BrandForms.alert(msg, title=title, yes=True, no=True))  # type: ignore
        except Exception:
            pass
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "confirm"):  # bootstrap
        return bool(_provider_mod.forms.confirm(msg, title=title))  # type: ignore
    if hasattr(_provider_mod, "alert"):  # pyRevit fallback (sometimes returns bool)
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
    if hasattr(_provider_mod, "input_box"):  # v6/v5
        try:
            return _provider_mod.input_box(title=title, label=prompt, default_text=default_text)  # type: ignore
        except TypeError:
            return _provider_mod.input_box(title, prompt, default_text)  # type: ignore
    if hasattr(_provider_mod, "BrandForms"):  # v4/v3
        return _provider_mod.BrandForms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore
    if hasattr(_provider_mod, "forms") and hasattr(_provider_mod.forms, "ask_for_string"):  # bootstrap
        return _provider_mod.forms.ask_for_string(prompt=prompt, default=default_text, title=title)  # type: ignore
    if hasattr(_provider_mod, "ask_for_string"):  # pyRevit
        return _provider_mod.ask_for_string(default=default_text)  # type: ignore
    return default_text or None

def ui_select(title: str, items: Iterable[Any], message: str | None = None, multi: bool = False):
    """Generic list picker. If no provider list UI exists, falls back to a simple alert + first item(s)."""
    items = list(items)
    # try optional bootstrap helper if present in your repo
    m_boot, _ = _load_file("ada_bootstrap.py")
    if m_boot and hasattr(m_boot, "_wf_select_from_list"):
        try:
            sfl = m_boot._wf_select_from_list()
            return sfl.show(items, title=title, multi=multi)  # type: ignore
        except Exception:
            pass
    ui_alert(message or "Select item(s) then press OK.", title=title)
    return items if (multi and items) else (items[0] if items else None)


# ── Back-compat `forms` adapter (pyRevit-style) ────────────────────────────────
# Many existing scripts expect: `from ada_core.ui_loader import forms` and then
# call either `forms.SelectFromList.show(...)` (class-style) or
# `forms.SelectFromList(...)` / `forms.select_from_list(...)` (callable-style).
# This adapter makes BOTH styles work uniformly across providers (v6/v5/v4/v3/
# bootstrap/pyRevit) and falls back to a minimal WinForms selector.

class _SelectFromListAdapter(object):
    \"\"\"Callable object that also exposes .show(...).\"\"\"
    def __call__(self, items, title=\"Select\", multiselect=False, ok_label=\"OK\", **kwargs):
        return self.show(items, title=title, button_name=ok_label, multiselect=multiselect, **kwargs)

    @staticmethod
    def show(options, title=\"Select\", button_name=\"OK\", multiselect=False, **kwargs):
        # 1) v6 direct function
        if _provider_mod is not None and hasattr(_provider_mod, \"select_from_list\") and callable(_provider_mod.select_from_list):
            try:
                # Map arguments into v6 signature
                return _provider_mod.select_from_list(
                    options,
                    title=title,
                    multiselect=bool(multiselect),
                    ok_label=str(button_name) if button_name else \"OK\",
                    cancel_label=\"Cancel\",
                    prompt=kwargs.get(\"prompt\"),
                    name_attr=kwargs.get(\"name_attr\"),
                    to_str=kwargs.get(\"to_str\"),
                )
            except Exception:
                pass

        # 2) v4/v3 BrandForms.SelectFromList.show(...)
        try:
            if _provider_mod is not None and hasattr(_provider_mod, \"BrandForms\") and hasattr(_provider_mod.BrandForms, \"SelectFromList\"):
                sfl = _provider_mod.BrandForms.SelectFromList
                if hasattr(sfl, \"show\"):
                    return sfl.show(options, title=title, button_name=button_name or \"OK\", multiselect=bool(multiselect))
        except Exception:
            pass

        # 3) bootstrap forms.SelectFromList (callable or object with .show)
        try:
            m_boot, _src = _load_file(\"ada_bootstrap.py\")
            if m_boot is not None and hasattr(m_boot, \"forms\"):
                sfl = getattr(m_boot.forms, \"SelectFromList\", None) or getattr(m_boot.forms, \"select_from_list\", None)
                if sfl is not None:
                    # callable style
                    if callable(sfl) and not hasattr(sfl, \"show\"):
                        return sfl(options, title=title, multiselect=bool(multiselect))
                    # object-with-show style
                    if hasattr(sfl, \"show\"):
                        return sfl.show(options, title=title, button_name=button_name or \"OK\", multiselect=bool(multiselect))
        except Exception:
            pass

        # 4) pyRevit forms (class with .show)
        try:
            from pyrevit import forms as _pv  # type: ignore
            if hasattr(_pv, \"SelectFromList\") and hasattr(_pv.SelectFromList, \"show\"):
                return _pv.SelectFromList.show(options, title=title, button_name=button_name or \"OK\", multiselect=bool(multiselect))
        except Exception:
            pass

        # 5) Final tiny fallback: use our ui_select() prompt then return first/selected
        return ui_select(title=title, items=options or [], multi=bool(multiselect))

class _FormsAdapter(object):
    # Normalized alert/confirm/input helpers (delegate to the unified helpers above)
    alert          = staticmethod(ui_alert)
    confirm        = staticmethod(ui_confirm)
    ask_yes_no     = staticmethod(lambda msg, title=\"Confirm\": bool(ui_confirm(msg, title)))
    ask_for_string = staticmethod(lambda prompt=\"\", title=\"Input\", default=\"\": ui_input(title, prompt, default))

    # List selectors: expose both classic and pythonic names
    SelectFromList   = _SelectFromListAdapter()
    select_from_list = SelectFromList

    # Convenience: expose a thin wrapper that mirrors old code patterns
    def big_button_box(self, title=\"Choose\", buttons=None, cancel=True):
        # Try to leverage ada_bootstrap's themed big buttons if available
        try:
            m_boot, _src = _load_file(\"ada_bootstrap.py\")
            if m_boot is not None and hasattr(m_boot, \"_big_button_box\") or hasattr(m_boot, \"big_button_box\"):
                fun = getattr(m_boot, \"_big_button_box\", None) or getattr(m_boot, \"big_button_box\", None)
                if callable(fun):
                    return fun(title=title, buttons=list(buttons or []), cancel=cancel)
        except Exception:
            pass
        # Otherwise fall back to a simple SelectFromList
        btns = list(buttons or [])
        if not btns:
            return None
        res = self.SelectFromList(btns, title=title, multiselect=False)
        return res

# Export `forms` and convenience free function `select_from_list` for new code
forms = _FormsAdapter()

def select_from_list(items, **kwargs):
    return forms.SelectFromList(items, **kwargs)

# Public symbols
try:
    __all__  # may not exist in earlier revisions
except NameError:
    __all__ = []
__all__ += [\"forms\", \"select_from_list\", \"ui_alert\", \"ui_confirm\", \"ui_input\", \"ui_select\", \"__ui_source__\"]
