# ada_core/viewports.py — viewport helpers (UI-free, defensive, additive)
from __future__ import annotations
from typing import Iterable, List, Optional, Sequence, Tuple, Callable

from Autodesk.Revit.DB import (  # type: ignore
    FilteredElementCollector, ElementType, Viewport, ViewSheet, View, XYZ,
    BuiltInParameter, ElementId
)

# Try to import the specific type (not always present on older APIs)
try:
    from Autodesk.Revit.DB import ViewportType  # type: ignore
    _HAS_VIEWPORTTYPE = True
except Exception:
    ViewportType = None  # type: ignore
    _HAS_VIEWPORTTYPE = False


# --------------------------- Discovery ---------------------------
def get_viewports_on_sheet(doc, sheet) -> List[Viewport]:
    """Return all Viewport instances placed on a given sheet."""
    try:
        return list(FilteredElementCollector(doc, sheet.Id).OfClass(Viewport))
    except Exception:
        return []


def find_viewport_type_by_name(doc, name_exact: str = "No Title") -> Optional[ElementType]:
    """
    Resolve a viewport type by its Name. Common case is 'No Title'.
    Tries DB.ViewportType first, then falls back to generic ElementType.
    """
    # Preferred: explicit ViewportType class
    if _HAS_VIEWPORTTYPE:
        try:
            for vt in FilteredElementCollector(doc).OfClass(ViewportType):
                nm = getattr(vt, "Name", None)
                if nm and str(nm).strip() == name_exact:
                    return vt
        except Exception:
            pass

    # Fallback: search all ElementType and compare the SYMBOL_NAME_PARAM
    try:
        for et in FilteredElementCollector(doc).OfClass(ElementType):
            try:
                p = et.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
                nm = str(p.AsString()) if p else (str(getattr(et, "Name", "")) or "")
                if nm.strip() == name_exact:
                    return et
            except Exception:
                continue
    except Exception:
        pass
    return None


def any_viewport_type(doc) -> Optional[ElementType]:
    """Return some valid viewport type (first found), or None."""
    if _HAS_VIEWPORTTYPE:
        try:
            for vt in FilteredElementCollector(doc).OfClass(ViewportType):
                return vt
        except Exception:
            pass
    try:
        for et in FilteredElementCollector(doc).OfClass(ElementType):
            # Heuristic: viewport types usually belong to the Viewport type family
            try:
                cat = getattr(et, "Category", None)
                if cat and "viewport" in cat.Name.lower():
                    return et
            except Exception:
                continue
    except Exception:
        pass
    return None


# --------------------------- Placement ---------------------------
def can_add_view(doc, sheet, view) -> bool:
    """Wrapper for Viewport.CanAddViewToSheet with guards."""
    try:
        return Viewport.CanAddViewToSheet(doc, sheet.Id, view.Id)
    except Exception:
        return False


def add_views_at_positions(
    doc,
    sheet,
    views: Sequence[View],
    positions: Sequence[XYZ],
    vptype: Optional[ElementType] = None,
    post_create: Optional[Callable[[Viewport, View], None]] = None,
) -> List[str]:
    """
    Adds each view to the sheet at the matching position.
    Expects an active Transaction outside.
    - vptype: ElementType or None; if provided, each new viewport will be switched to this type.
    - post_create(viewport, view): optional callback to tweak (e.g., row alignment, hide bubbles)
    Returns list of successfully placed view names.
    """
    placed = []
    n = min(len(views), len(positions))
    for i in range(n):
        v = views[i]
        pos = positions[i]
        try:
            if not can_add_view(doc, sheet, v):
                continue
            vp = Viewport.Create(doc, sheet.Id, v.Id, pos)
            if vptype is not None:
                try:
                    vp.ChangeTypeId(vptype.Id)
                except Exception:
                    pass
            if post_create is not None:
                try:
                    post_create(vp, v)
                except Exception:
                    pass
            placed.append(v.Name)
        except Exception:
            continue
    return placed


# --------------------------- Editing & Alignment ---------------------------
def change_all_viewports_type_on_sheet(doc, sheet, vptype: ElementType) -> int:
    """Change the type of every viewport on a sheet; returns count changed."""
    count = 0
    for vp in get_viewports_on_sheet(doc, sheet):
        try:
            if vp and vptype and vp.GetTypeId() != vptype.Id:
                vp.ChangeTypeId(vptype.Id)
                count += 1
        except Exception:
            continue
    return count


def set_all_viewports_no_title(doc, sheet, name_exact: str = "No Title") -> int:
    """
    Convenience: find type named 'No Title' (or provided string) and apply to all viewports.
    Returns number changed. If not found, returns 0.
    """
    vt = find_viewport_type_by_name(doc, name_exact)
    if not vt:
        return 0
    return change_all_viewports_type_on_sheet(doc, sheet, vt)


def viewport_box_center(vp) -> Optional[XYZ]:
    """Return the viewport box center if available (sheet coords)."""
    try:
        if hasattr(vp, "GetBoxCenter"):
            return vp.GetBoxCenter()
        # Fallback via outline
        if hasattr(vp, "GetBoxOutline"):
            ol = vp.GetBoxOutline()
            minp, maxp = ol.MinimumPoint, ol.MaximumPoint
            return XYZ((minp.X + maxp.X)/2.0, (minp.Y + maxp.Y)/2.0, 0.0)
    except Exception:
        pass
    return None


def align_rows_by_y(sheet, tolerance_ft: float = 1e-6) -> int:
    """
    Aligns viewports on a sheet into rows by snapping Y to row-average for clusters.
    Returns number of viewports adjusted.
    NOTE: Expects an active Transaction.
    """
    vps = get_viewports_on_sheet(sheet.Document, sheet)
    if not vps:
        return 0
    # Build clusters keyed by rounded Y
    rows = {}
    for vp in vps:
        c = viewport_box_center(vp)
        if not c:
            continue
        key = round(c.Y / max(tolerance_ft, 1e-9), 0)
        rows.setdefault(key, []).append((vp, c))
    changed = 0
    for _, items in rows.items():
        if len(items) < 2:
            continue
        avg_y = sum(c.Y for _, c in items) / float(len(items))
        for vp, c in items:
            try:
                vp.SetBoxCenter(XYZ(c.X, avg_y, 0.0))
                changed += 1
            except Exception:
                continue
    return changed


def nudge_all_viewports(sheet, dx_ft: float = 0.0, dy_ft: float = 0.0) -> int:
    """
    Move every viewport by the same delta in sheet coordinates.
    Returns number moved.
    NOTE: Expects an active Transaction.
    """
    vps = get_viewports_on_sheet(sheet.Document, sheet)
    if not vps or (dx_ft == 0.0 and dy_ft == 0.0):
        return 0
    moved = 0
    for vp in vps:
        try:
            c = viewport_box_center(vp)
            if not c:
                continue
            vp.SetBoxCenter(XYZ(c.X + dx_ft, c.Y + dy_ft, 0.0))
            moved += 1
        except Exception:
            continue
    return moved


__all__ = [
    "get_viewports_on_sheet",
    "find_viewport_type_by_name",
    "any_viewport_type",
    "can_add_view",
    "add_views_at_positions",
    "change_all_viewports_type_on_sheet",
    "set_all_viewports_no_title",
    "viewport_box_center",
    "align_rows_by_y",
    "nudge_all_viewports",
]
