#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.runtime
Lightweight runtime helpers for pyRevit/Revit scripts.
"""

from typing import Tuple

def get_doc_uidoc():
    """Return (uidoc, doc) from pyRevit runtime via __revit__ (unchanged)."""
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    return uidoc, uidoc.Document

def get_uiapp_app() -> Tuple[object, object]:
    """
    Return (uiapp, app) using the same __revit__ handle.
    New function — safe to add; does not affect existing imports.
    """
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    uiapp = uidoc.Application
    app = uiapp.Application
    return uiapp, app

def safe_get_doc_uidoc() -> Tuple[object, object]:
    """
    Optional convenience: if __revit__ is missing for any reason,
    fall back to pyrevit.revit. New function; won’t affect old code.
    """
    try:
        return get_doc_uidoc()
    except Exception:
        from pyrevit import revit  # type: ignore
        return revit.uidoc, revit.doc
