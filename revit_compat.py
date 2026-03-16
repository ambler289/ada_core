# -*- coding: utf-8 -*-
"""
ADa Revit Compatibility Layer

Provides a stable interface for accessing Revit context objects.
Allows legacy scripts that use:

    from ada_core import revit_compat as revit

to continue working.

Future scripts should prefer:
    from ada_core import revit
"""

from __future__ import annotations

# pyRevit context
from pyrevit import revit as _pyrevit_revit  # type: ignore


# -------------------------------------------------------------------
# Core Revit Context
# -------------------------------------------------------------------

doc = _pyrevit_revit.doc
uidoc = _pyrevit_revit.uidoc
uiapp = __revit__ # type: ignore
app = doc.Application if doc else None


# -------------------------------------------------------------------
# Convenience Helpers
# -------------------------------------------------------------------

def get_doc():
    """Return active document."""
    return doc


def get_uidoc():
    """Return active UIDocument."""
    return uidoc


def get_app():
    """Return Revit application."""
    return app


def get_uiapp():
    """Return Revit UI application."""
    return uiapp


# -------------------------------------------------------------------
# Selection Helpers
# -------------------------------------------------------------------

def get_selection():
    """Return current Revit selection."""
    if uidoc:
        return list(uidoc.Selection.GetElementIds())
    return []


def get_selected_elements():
    """Return selected elements."""
    if not uidoc:
        return []

    ids = uidoc.Selection.GetElementIds()
    return [doc.GetElement(i) for i in ids]


# -------------------------------------------------------------------
# Active View
# -------------------------------------------------------------------

def get_active_view():
    """Return active view."""
    if doc:
        return doc.ActiveView
    return None


# -------------------------------------------------------------------
# Debug
# -------------------------------------------------------------------

def context_summary():
    """Return simple context summary for diagnostics."""
    return {
        "doc": str(doc.Title) if doc else None,
        "view": str(doc.ActiveView.Name) if doc else None,
        "selection_count": len(get_selection())
    }