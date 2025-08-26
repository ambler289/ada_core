# ada_core/ui.py
# -----------------------------------------------------------------------------
# Unified UI helpers (v6 themed → ada_bootstrap → pyrevit → console)
# Backward compatible with existing "alert", "confirm", "choose_yes_no",
# and "ask_string". Adds safe, new helpers that won't clash:
# - big_buttons(title, options, message=None, cancel=True)
# - select_from_list(items, title="Select", multiselect=False, name_attr=None)
# - ask_int(prompt, default=None, title=None)
# - ask_float(prompt, default=None, title=None)
# Also exposes UI_SOURCE (string) for diagnostics.
# -----------------------------------------------------------------------------

from __future__ import print_function

import os
import sys

UI_SOURCE = "console"   # updated after backend discovery


# --- internal: try to make ada_brandforms_v6 importable if ADA_UI_DIR is given
def _ensure_ada_ui_path():
    hint = os.getenv("ADA_UI_DIR")
    if hint and os.path.isdir(hint) and hint not in sys.path:
        sys.path.insert(0, hint)

_ensure_ada_ui_path()


# --- backend discovery --------------------------------------------------------
def _backend():
    """Return a lightweight object with 'name' and a few callables:
       alert(msg, title=...), buttons(title, message, options)
       ask_string(prompt, default=None, title=...)
       select_from_list(items, title, multiselect, name_attr)
    """
    # 1) Themed v6 buttons/alert
    try:
        from ada_brandforms_v6 import alert as v6_alert  # type: ignore

        class V6(object):
            name = "ada_brandforms_v6"

            @staticmethod
            def alert(msg, title="Message", **_):
                return v6_alert(str(msg), title=str(title))

            @staticmethod
            def buttons(title, message, options, cancel=True):
                rv = v6_alert(str(message or ""), title=str(title or ""),
                              buttons=list(options or []))
                if isinstance(rv, (list, tuple)):
                    return rv[0] if rv else None
                return rv

            # v6 does not provide a native ask_string; fall back later.
            ask_string = None
            select_from_list = None

        return V6
    except Exception:
        pass

    # 2) ada_bootstrap.forms (your brand wrappers)
    try:
        from ada_bootstrap import forms as F  # type: ignore

        class Boot(object):
            name = "ada_bootstrap.forms"
            alert = staticmethod(F.alert)

            @staticmethod
            def buttons(title, message, options, cancel=True):
                rv = getattr(F, "big_button_box")(title=title,
                                                  buttons=list(options or []),
                                                  cancel=bool(cancel))
                if isinstance(rv, (list, tuple)):
                    return rv[0] if rv else None
                return rv

            @staticmethod
            def ask_string(prompt, default=None, title=None):
                fun = getattr(F, "ask_for_string", None)
                if callable(fun):
                    return fun(prompt=str(prompt),
                               default=default,
                               title=title or "Input")
                return None

            select_from_list = None

        return Boot
    except Exception:
        pass

    # 3) pyRevit forms
    try:
        from pyrevit import forms as PF  # type: ignore

        class PyR(object):
            name = "pyrevit.forms"

            @staticmethod
            def alert(msg, title="Message", **kw):
                # tolerate missing kwargs on some pyrevit builds
                try:
                    return PF.alert(str(msg), title=title, **kw)
                except TypeError:
                    return PF.alert(str(msg), title=title)

            @staticmethod
            def buttons(title, message, options, cancel=True):
                if hasattr(PF, "CommandSwitchWindow"):
                    rv = PF.CommandSwitchWindow.show(list(options or []),
                                                     message=message or "",
                                                     title=title or "Select")
                    if isinstance(rv, (list, tuple)):
                        return rv[0] if rv else None
                    return rv
                return None

            @staticmethod
            def ask_string(prompt, default=None, title=None):
                fn = getattr(PF, "ask_for_string", None)
                if callable(fn):
                    return fn(prompt=str(prompt),
                              default=default,
                              title=title or "Input")
                return None

            @staticmethod
            def select_from_list(items, title="Select", multiselect=False, name_attr=None):
                # Prefer pyRevit native if available
                SFL = getattr(PF, "SelectFromList", None)
                if not SFL:
                    return None
                if name_attr:
                    # build list of display items with attr
                    data = [SFL.listitem(getattr(it, name_attr, str(it)), it) for it in items]
                else:
                    data = [SFL.listitem(str(it), it) for it in items]
                sel = SFL.show(data,
                               title=title,
                               multiselect=bool(multiselect))
                if not sel:
                    return [] if multiselect else None
                if multiselect:
                    return [li.value for li in sel]
                return sel if isinstance(sel, (str,)) else getattr(sel, "value", sel)

        return PyR
    except Exception:
        pass

    # 4) console fallback
    class Console(object):
        name = "console"

        @staticmethod
        def alert(msg, title="Message", **_):
            print("\n[{}] {}\n{}".format(title, "-"*max(3, len(title)), msg))

        @staticmethod
        def buttons(title, message, options, cancel=True):
            print("\n{}\n{}\n".format(title or "Choose", message or ""))
            options = list(options or [])
            for i, op in enumerate(options, 1):
                print("{:>2}) {}".format(i, op))
            try:
                raw = input("\nEnter number (blank cancels): ").strip()
                if not raw:
                    return None
                idx = int(raw) - 1
                return options[idx] if 0 <= idx < len(options) else None
            except Exception:
                return None

        @staticmethod
        def ask_string(prompt, default=None, title=None):
            try:
                raw = input("{} ".format(prompt))
                return raw if raw else default
            except Exception:
                return default

        @staticmethod
        def select_from_list(items, title="Select", multiselect=False, name_attr=None):
            lbls = [getattr(it, name_attr, str(it)) if name_attr else str(it) for it in items]
            print("\n{}".format(title))
            for i, s in enumerate(lbls, 1):
                print("{:>2}) {}".format(i, s))
            if multiselect:
                raw = input("Enter numbers (comma-separated): ").strip()
                if not raw:
                    return []
                idxs = []
                for token in raw.split(","):
                    try:
                        idxs.append(int(token) - 1)
                    except Exception:
                        pass
                return [items[i] for i in idxs if 0 <= i < len(items)]
            else:
                raw = input("Enter number: ").strip()
                try:
                    idx = int(raw) - 1
                    return items[idx] if 0 <= idx < len(items) else None
                except Exception:
                    return None

    return Console


# cache backend and set UI_SOURCE
_backend_obj = _backend()
UI_SOURCE = getattr(_backend_obj, "name", "console")


# --- public, back-compatible API ---------------------------------------------
def _forms():
    """Kept for compatibility with older imports that expected a forms-like object."""
    # Not returning a real forms module anymore; leave as shim for legacy code.
    return None


def alert(message, title=None):
    try:
        return _backend_obj.alert(str(message), title=title or "Message")
    except Exception:
        print("\n[ALERT{}]\n{}\n".format(" - "+(title or "") if title else "", message))


def confirm(message, title="Confirm"):
    """Yes/No; returns bool."""
    # v6 & buttons backends: show 2 buttons
    btn = _backend_obj.buttons(title, message, ["Yes", "No"])
    if btn in ("Yes", "No"):
        return btn == "Yes"
    # Try pyRevit alert yes/no signature if available
    try:
        from pyrevit import forms as PF  # type: ignore
        return bool(PF.alert(str(message), title=title, yes=True, no=True))
    except Exception:
        pass
    # console
    try:
        raw = input("{} [y/N]: ".format(message))
        return raw.strip().lower().startswith("y")
    except Exception:
        return False


def choose_yes_no(message, title="Choose", yes="Yes", no="No"):
    btn = _backend_obj.buttons(title, message, [yes, no])
    if btn == yes:
        return True
    if btn == no:
        return False
    return confirm("{} [{} / {}]".format(message, yes, no), title)


def ask_string(prompt, default=None, title=None):
    fn = getattr(_backend_obj, "ask_string", None)
    if callable(fn):
        val = fn(prompt, default=default, title=title)
        if val is not None:
            return val
    try:
        raw = input("{} ".format(prompt))
        return raw if raw else default
    except Exception:
        return default


# --- safe new helpers (non-breaking) -----------------------------------------
def big_buttons(title, options, message=None, cancel=True):
    """Return clicked label or None."""
    return _backend_obj.buttons(title, message or "", list(options or []), cancel=bool(cancel))


def select_from_list(items, title="Select", multiselect=False, name_attr=None):
    """Return one item (or list of items if multiselect=True)."""
    fn = getattr(_backend_obj, "select_from_list", None)
    if callable(fn):
        return fn(items, title=title, multiselect=multiselect, name_attr=name_attr)

    # Fallbacks if backend has only single-choice buttons:
    if not multiselect:
        labels = [getattr(it, name_attr, str(it)) if name_attr else str(it) for it in items]
        choice = big_buttons(title, labels)
        if choice is None:
            return None
        # map back to item
        for it, lbl in zip(items, labels):
            if lbl == choice:
                return it
        return None

    # Console-like multi-select as last resort
    return _backend().select_from_list(items, title=title, multiselect=True, name_attr=name_attr)


def ask_int(prompt, default=None, title=None):
    """Numeric input helper that wraps ask_string."""
    s = ask_string(prompt, default=None, title=title)
    if s is None or s == "":
        return default
    try:
        return int(str(s).strip())
    except Exception:
        return default


def ask_float(prompt, default=None, title=None):
    s = ask_string(prompt, default=None, title=title)
    if s is None or s == "":
        return default
    try:
        return float(str(s).strip())
    except Exception:
        return default


# --- vNext themed wrappers (non-breaking aliases) ----------------------------
def alert_v6(msg, title="Message"):
    """Prefer v6 themed alert; gracefully falls back."""
    try:
        from ada_brandforms_v6 import alert as v6_alert  # type: ignore
        return v6_alert(str(msg), title=str(title))
    except Exception:
        return alert(msg, title=title)


def confirm_v6(msg, title="Confirm"):
    btn = big_buttons(title, ["Yes", "No"], message=msg)
    if btn in ("Yes", "No"):
        return btn == "Yes"
    return confirm(msg, title)
