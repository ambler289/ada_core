# Unified UI helpers (ada_bootstrap → pyrevit.forms → print)
# Backward compatible with existing "alert" and "ask_string".
# Adds: confirm(), choose_yes_no() with consistent signatures.

def _forms():
    try:
        from ada_bootstrap import forms as F  # your branded forms
        return F
    except Exception:
        try:
            from pyrevit import forms as F  # type: ignore
            return F
        except Exception:
            return None

def alert(message, title=None):
    F = _forms()
    if F:
        try:
            # Prefer kwargs if available (ada_bootstrap)
            return F.alert(str(message), title=title) if title else F.alert(str(message))
        except Exception:
            pass
    print("\n[ALERT{}]\n{}\n".format(" - "+title if title else "", message))

def confirm(message, title="Confirm"):
    F = _forms()
    if F:
        try:
            return F.alert(str(message), title=title, yes=True, no=True)
        except Exception:
            pass
    resp = None
    try:
        raw = input("{} [y/N]: ".format(message))
        resp = raw.strip().lower().startswith("y")
    except Exception:
        resp = False
    return resp

def choose_yes_no(message, title="Choose", yes="Yes", no="No"):
    F = _forms()
    if F:
        try:
            return F.alert("{}\n\nYes: {}\nNo: {}".format(message, yes, no), title=title, yes=True, no=True)
        except Exception:
            pass
    return confirm(message + " [{} / {}]".format(yes, no), title)

def ask_string(prompt, default=None, title=None):
    F = _forms()
    if F:
        try:
            return F.ask_for_string(prompt=str(prompt), default=default, title=title or "Input")
        except Exception:
            pass
    try:
        raw = input("{} ".format(prompt))
        return raw if raw else default
    except Exception:
        return default
# ================= vNext safe additions (append-only) ==================
# Themed dialogs from FIRST call without touching existing names.

def _ada_v6_buttons(title, message, buttons):
    try:
        from ada_brandforms_v6 import alert as v6_alert  # type: ignore
        rv = v6_alert(str(message or ""), title=str(title or ""), buttons=list(buttons or []))
        if isinstance(rv, (list, tuple)):
            return rv[0] if rv else None
        return rv
    except Exception:
        return None

def alert_v6(msg, title="Message"):
    """Themed alert preferred (v6-first)."""
    try:
        from ada_brandforms_v6 import alert as v6_alert  # type: ignore
        return v6_alert(str(msg), title=str(title))
    except Exception:
        try:
            from pyrevit import forms  # type: ignore
            return forms.alert(str(msg), title=title)
        except Exception:
            print("[ALERT]", title, msg)

def confirm_v6(msg, title="Confirm"):
    """Themed Yes/No; returns bool. Never overrides existing confirm()."""
    rv = _ada_v6_buttons(title, msg, ["Yes", "No"])
    if rv in ("Yes", "No"):
        return rv == "Yes"
    try:
        from pyrevit import forms  # type: ignore
        return bool(forms.alert(str(msg), title=title, yes=True, no=True))
    except Exception:
        return True

def big_buttons(title, options, message=None, cancel=True):
    """Three-button style chooser.
    Order: v6 alert-with-buttons → ada_bootstrap.big_button_box → pyRevit CommandSwitchWindow.
    Returns clicked label or None.  Safe new name; does not shadow existing APIs.
    """
    rv = _ada_v6_buttons(title, message or "", options)
    if rv:
        return rv
    try:
        from ada_bootstrap import forms  # type: ignore
        rv = getattr(forms, "big_button_box")(title=title, buttons=list(options), cancel=bool(cancel))
        if rv:
            return rv
    except Exception:
        pass
    try:
        from pyrevit import forms as PF  # type: ignore
        if hasattr(PF, "CommandSwitchWindow"):
            rv = PF.CommandSwitchWindow.show(list(options), message=message or "", title=title)
            if isinstance(rv, (list, tuple)):
                return rv[0] if rv else None
            return rv
    except Exception:
        pass
    return None
