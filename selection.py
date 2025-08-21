#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.selection (BC-compatible)
- Preserves: preselected_of_types, pick_until_esc, preselected_textnotes, pick_textnotes
- Adds: safe_pick (Esc->None), pick_elements_by_category (BICs), unique_only toggle
"""

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from typing import List, Tuple, Any, Optional, Iterable
from Autodesk.Revit.DB import Element, TextNote, BuiltInCategory  # type: ignore
from Autodesk.Revit.Exceptions import OperationCanceledException  # type: ignore
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # type: ignore


class _TypeFilter(ISelectionFilter):
    def __init__(self, allowed_types: Tuple[Any, ...]):
        self._allowed = tuple(allowed_types) if allowed_types else tuple()

    def AllowElement(self, element):  # noqa: N802
        if not self._allowed:
            return True
        for t in self._allowed:
            try:
                if isinstance(element, t):
                    return True
            except Exception:
                pass
        return False

    def AllowReference(self, reference, position):  # noqa: N802
        return False


def preselected_of_types(uidoc, doc, *allowed_types) -> List[Element]:
    """Return preselected elements filtered by the given types. Accepts *types or a single sequence."""
    if len(allowed_types) == 1 and isinstance(allowed_types[0], (list, tuple)):
        allowed: Tuple[Any, ...] = tuple(allowed_types[0])
    else:
        allowed = tuple(allowed_types)

    ids = list(uidoc.Selection.GetElementIds())
    if not ids:
        return []

    out: List[Element] = []
    for eid in ids:
        el = doc.GetElement(eid)
        if el is None:
            continue
        if not allowed:
            out.append(el)
        else:
            for t in allowed:
                try:
                    if isinstance(el, t):
                        out.append(el)
                        break
                except Exception:
                    pass
    return out


def pick_until_esc(uidoc, doc, prompt: str, *allowed_types) -> List[Element]:
    """Click elements of given types one-by-one until the user presses Esc. Returns list without duplicates."""
    if len(allowed_types) == 1 and isinstance(allowed_types[0], (list, tuple)):
        allowed: Tuple[Any, ...] = tuple(allowed_types[0])
    else:
        allowed = tuple(allowed_types)

    fil = _TypeFilter(allowed) if allowed else None
    picked: List[Element] = []
    while True:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, fil, prompt) if fil else uidoc.Selection.PickObject(ObjectType.Element, prompt)
            el = doc.GetElement(ref.ElementId)
            if el and el not in picked:
                picked.append(el)
        except OperationCanceledException:
            break
    return picked


def preselected_textnotes(uidoc, doc) -> List[TextNote]:
    """Return preselected TextNotes if any, else []."""
    return preselected_of_types(uidoc, doc, (TextNote,))


def pick_textnotes(uidoc, doc, prompt="Click TextNotes one by one (Esc when done)") -> List[TextNote]:
    """Click TextNotes until Esc; filter on Python side to avoid ISelectionFilter quirks."""
    picked: List[TextNote] = []
    while True:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, prompt)
            el = doc.GetElement(ref.ElementId)
            if isinstance(el, TextNote) and el not in picked:
                picked.append(el)
        except OperationCanceledException:
            break
    return picked


# ---- New, non-breaking helpers ----
def safe_pick(uidoc, doc, prompt="Pick element", allowed_types=None):
    """Pick a single element; return None on Esc. Optionally restrict to types."""
    try:
        fil = _TypeFilter(tuple(allowed_types)) if allowed_types else None
        ref = uidoc.Selection.PickObject(ObjectType.Element, fil, prompt) if fil else uidoc.Selection.PickObject(ObjectType.Element, prompt)
        return doc.GetElement(ref.ElementId)
    except OperationCanceledException:
        return None


def pick_elements_by_category(uidoc, doc, prompt, categories: Iterable[BuiltInCategory], unique_only=True) -> List[Element]:
    """Pick-until-Esc for specific BuiltInCategories; returns elements (unique if unique_only)."""
    cats = set(int(c) for c in categories or [])
    picked = []

    class _CatFilter(ISelectionFilter):
        def AllowElement(self, e):
            try:
                return e.Category and e.Category.Id.IntegerValue in cats if cats else True
            except Exception:
                return False
        def AllowReference(self, r, p): return False

    fil = _CatFilter()
    seen_ids = set()
    while True:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, fil, prompt)
            el = doc.GetElement(ref.ElementId)
            if not el: 
                continue
            if unique_only:
                if el.Id.IntegerValue in seen_ids:
                    continue
                seen_ids.add(el.Id.IntegerValue)
            picked.append(el)
        except OperationCanceledException:
            break
    return picked

# ================= vNext safe additions (append-only; idempotent) ==================
# Each helper is defined only if it's not already present in this module.

# --- Safe TextNote selection trio (preselect → pick-until-Esc) ---------------------
if 'preselected_textnotes_safe' not in globals():
    def preselected_textnotes_safe(uidoc, doc):
        """Return preselected TextNote elements (no type imports required)."""
        out = []
        try:
            ids = list(uidoc.Selection.GetElementIds())
            for eid in ids:
                el = doc.GetElement(eid)
                if el and getattr(el.GetType(), "Name", "") == "TextNote":
                    out.append(el)
        except Exception:
            pass
        return out

if 'pick_textnotes_safe' not in globals():
    def pick_textnotes_safe(uidoc, doc, prompt="Click TextNotes (Esc when done)"):
        """Pick TextNotes until Esc. Fallback-only implementation."""
        picked = []
        try:
            from Autodesk.Revit.UI.Selection import ObjectType  # type: ignore
            from Autodesk.Revit.Exceptions import OperationCanceledException  # type: ignore
            while True:
                try:
                    ref = uidoc.Selection.PickObject(ObjectType.Element, prompt)
                    el = doc.GetElement(ref.ElementId)
                    if el and getattr(el.GetType(), "Name", "") == "TextNote" and el not in picked:
                        picked.append(el)
                except OperationCanceledException:
                    break
        except Exception:
            return []
        return picked

if 'get_textnotes_safe' not in globals():
    def get_textnotes_safe(uidoc, doc):
        """Preselection first; else pick until Esc."""
        notes = preselected_textnotes_safe(uidoc, doc)
        return notes if notes else pick_textnotes_safe(uidoc, doc)

# --- Single-pick helper with Esc=None ---------------------------------------------
if 'safe_pick' not in globals():
    def safe_pick(uidoc, doc, prompt="Pick element", allowed_types=None):
        """Pick a single element; return None on Esc. Optionally restrict to types."""
        try:
            from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter  # type: ignore
            from Autodesk.Revit.Exceptions import OperationCanceledException  # type: ignore

            fil = None
            if allowed_types:
                class _TypeFilter(ISelectionFilter):
                    def __init__(self, ts): self._t = tuple(ts)
                    def AllowElement(self, e):
                        for t in self._t:
                            try:
                                if isinstance(e, t): return True
                            except Exception:
                                pass
                        return False
                    def AllowReference(self, r, p): return False
                fil = _TypeFilter(tuple(allowed_types))

            ref = uidoc.Selection.PickObject(ObjectType.Element, fil, prompt) if fil else uidoc.Selection.PickObject(ObjectType.Element, prompt)
            return doc.GetElement(ref.ElementId)
        except OperationCanceledException:
            return None
        except Exception:
            return None

# --- Category-filtered pick-until-Esc ---------------------------------------------
if 'pick_elements_by_category' not in globals():
    def pick_elements_by_category(uidoc, doc, prompt, categories, unique_only=True):
        """Pick-until-Esc for specific BuiltInCategories; returns elements (unique if unique_only)."""
        try:
            from Autodesk.Revit.DB import BuiltInCategory  # type: ignore
            from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter  # type: ignore
            from Autodesk.Revit.Exceptions import OperationCanceledException  # type: ignore
        except Exception:
            return []

        cats = set(int(c) for c in (categories or []))

        class _CatFilter(ISelectionFilter):
            def AllowElement(self, e):
                try:
                    return e.Category and e.Category.Id.IntegerValue in cats if cats else True
                except Exception:
                    return False
            def AllowReference(self, r, p): return False

        fil = _CatFilter()
        picked, seen = [], set()
        while True:
            try:
                ref = uidoc.Selection.PickObject(ObjectType.Element, fil, prompt)
                el = doc.GetElement(ref.ElementId)
                if not el:
                    continue
                if unique_only:
                    key = getattr(getattr(el, "Id", None), "IntegerValue", None)
                    if key in seen:
                        continue
                    if key is not None:
                        seen.add(key)
                picked.append(el)
            except OperationCanceledException:
                break
        return picked
