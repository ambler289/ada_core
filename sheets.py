# ada_core/sheets.py — sheet & titleblock helpers (UI-free, defensive)
from __future__ import annotations
from typing import Optional, Dict, Tuple, Iterable
import re

from Autodesk.Revit.DB import (  # type: ignore
    FilteredElementCollector, BuiltInCategory, BuiltInParameter,
    ViewSheet, Viewport, FamilyInstance, ElementId, XYZ
)

from ada_core.units import mm_to_ft, ft_to_mm
from ada_core.params import try_param_length_mm

# --------------------------- Core lookups ---------------------------
def get_titleblock_instance(doc, sheet) -> Optional[FamilyInstance]:
    """Return the first titleblock instance placed on a sheet (if any)."""
    try:
        blocks = list(FilteredElementCollector(doc, sheet.Id).OfCategory(BuiltInCategory.OST_TitleBlocks))
        return blocks[0] if blocks else None
    except Exception:
        return None

def get_sheet_size_mm(sheet) -> Tuple[float, float]:
    """
    Sheet size (width_mm, height_mm) from sheet parameters.
    If unavailable, returns (0.0, 0.0).
    """
    try:
        w_p = sheet.get_Parameter(BuiltInParameter.SHEET_WIDTH)
        h_p = sheet.get_Parameter(BuiltInParameter.SHEET_HEIGHT)
        if w_p and h_p:
            return (ft_to_mm(w_p.AsDouble()), ft_to_mm(h_p.AsDouble()))
    except Exception:
        pass
    return (0.0, 0.0)

# --------------------------- Margins & paper ---------------------------
def _tb_type_param_mm(tb_type, name: str) -> Optional[float]:
    try:
        p = tb_type.LookupParameter(name)
        return try_param_length_mm(p) if p else None
    except Exception:
        return None

def _resolve_common_margins_mm(tb_type) -> Dict[str, float]:
    """
    Probe common custom parameters on the titleblock TYPE to infer margins.
    Known patterns at ADa (customise in one place if naming changes):
      - 'TB - h offset'  (horizontal offset on both sides)
      - 'TB - v offset'  (vertical offset on both sides)
      - 'Binding Edge'   (extra left margin)
    Falls back to zeros.
    """
    left = right = top = bottom = 0.0
    try:
        off_h = _tb_type_param_mm(tb_type, "TB - h offset") or 0.0
        off_v = _tb_type_param_mm(tb_type, "TB - v offset") or 0.0
        bind  = _tb_type_param_mm(tb_type, "Binding Edge")   or 0.0
        left   = max(off_h, bind)
        right  = off_h
        top    = off_v
        bottom = off_v
    except Exception:
        pass
    return dict(left_mm=float(left), right_mm=float(right),
                top_mm=float(top), bottom_mm=float(bottom))

def sheet_paper_and_margins_mm(doc, sheet, overrides: Dict[str, float] = None) -> Dict[str, float]:
    """
    Return a dictionary with paper size and margins (mm):
      { width_mm, height_mm, left_mm, right_mm, top_mm, bottom_mm }
    - Uses sheet's SHEET_WIDTH/HEIGHT for paper size.
    - Infers margins from titleblock TYPE custom params (see above).
    - 'overrides' lets you supply explicit margin values (any subset).
    """
    w_mm, h_mm = get_sheet_size_mm(sheet)
    tb = get_titleblock_instance(doc, sheet)
    margins = dict(left_mm=0.0, right_mm=0.0, top_mm=0.0, bottom_mm=0.0)
    if tb:
        tb_type = doc.GetElement(tb.GetTypeId())
        margins = _resolve_common_margins_mm(tb_type)
    if overrides:
        margins.update({k: float(v) for k, v in overrides.items() if k in margins})
    return dict(width_mm=float(w_mm), height_mm=float(h_mm), **margins)

def iso_class_from_mm(w_mm: float, h_mm: float, tol: float = 5.0) -> str:
    """Classify A-series size by dims (±tol mm). Returns 'A1'/'A2'/'A3'/'CUSTOM'."""
    W, H = (max(w_mm, h_mm), min(w_mm, h_mm))
    close = lambda a, b: abs(a - b) <= tol
    if close(W, 841) and close(H, 594): return 'A1'
    if close(W, 594) and close(H, 420): return 'A2'
    if close(W, 420) and close(H, 297): return 'A3'
    return 'CUSTOM'

def sheet_capacity(doc, sheet, base_a3_cap: int = 15, cap_limit: int = 120) -> int:
    """
    Heuristic capacity (how many similarly sized small viewports fit).
    Scales A3→A2→A1 approximately by area; clamps to cap_limit.
    """
    info = sheet_paper_and_margins_mm(doc, sheet) or {}
    w, h = float(info.get('width_mm', 0.0)), float(info.get('height_mm', 0.0))
    if w <= 0 or h <= 0:
        return base_a3_cap
    iso = iso_class_from_mm(w, h)
    if iso == 'A3': cap = base_a3_cap
    elif iso == 'A2': cap = int(round(base_a3_cap * 2.0))
    elif iso == 'A1': cap = int(round(base_a3_cap * 4.0))
    else:
        a3_area = 420.0 * 297.0
        cap = int(max(1, round(base_a3_cap * ((w * h) / max(1.0, a3_area)))))
    return int(min(cap_limit, cap))

# --------------------------- Placement areas ---------------------------
def _tb_bbox_on_sheet(doc, sheet):
    tb = get_titleblock_instance(doc, sheet)
    if not tb:
        return None
    try:
        return tb.get_BoundingBox(sheet)
    except Exception:
        return None

def area_from_margins(doc, sheet, margins_mm: Dict[str, float]) -> Tuple[Optional[XYZ], Optional[XYZ]]:
    """
    Compute a placement rectangle (top-left XYZ, bottom-right XYZ) inside titleblock bbox,
    inset by margins (mm). Returns (None, None) if not available.
    """
    bb = _tb_bbox_on_sheet(doc, sheet)
    if not bb:
        return (None, None)
    left   = bb.Min.X + mm_to_ft(margins_mm.get('left_mm', 0.0))
    right  = bb.Max.X - mm_to_ft(margins_mm.get('right_mm', 0.0))
    bottom = bb.Min.Y + mm_to_ft(margins_mm.get('bottom_mm', 0.0))
    top    = bb.Max.Y - mm_to_ft(margins_mm.get('top_mm', 0.0))
    if right <= left or top <= bottom:
        return (None, None)
    return (XYZ(left, top, 0), XYZ(right, bottom, 0))

def clamp_area_to_margins(doc, sheet, p1: XYZ, p2: XYZ, margins_mm: Dict[str, float]) -> Tuple[XYZ, XYZ]:
    """
    Clamp any picked rectangle to live within titleblock bbox minus margins.
    Returns adjusted (top-left, bottom-right). If clamping impossible, returns inputs.
    """
    bb = _tb_bbox_on_sheet(doc, sheet)
    if not bb:
        return (p1, p2)
    left   = bb.Min.X + mm_to_ft(margins_mm.get('left_mm', 0.0))
    right  = bb.Max.X - mm_to_ft(margins_mm.get('right_mm', 0.0))
    bottom = bb.Min.Y + mm_to_ft(margins_mm.get('bottom_mm', 0.0))
    top    = bb.Max.Y - mm_to_ft(margins_mm.get('top_mm', 0.0))

    x1, x2 = sorted([p1.X, p2.X])
    y1, y2 = sorted([p1.Y, p2.Y])
    x1 = max(x1, left);  x2 = min(x2, right)
    y1 = max(y1, bottom); y2 = min(y2, top)
    if x2 <= x1 or y2 <= y1:
        return (p1, p2)
    return (XYZ(x1, y2, 0), XYZ(x2, y1, 0))

# --------------------------- Sheet finders ---------------------------
def find_sheets_by_title(doc, pattern: str, regex: bool = False) -> Iterable[ViewSheet]:
    """
    Yield sheets whose Title matches pattern.
    - If regex=False (default), case-insensitive substring match is used.
    - If regex=True, 'pattern' is treated as a regular expression.
    """
    r = re.compile(pattern, re.IGNORECASE) if regex else None
    for s in FilteredElementCollector(doc).OfClass(ViewSheet):
        try:
            title = s.Title or ""
            if regex:
                if r.search(title): yield s
            else:
                if pattern.lower() in title.lower(): yield s
        except Exception:
            continue

def list_sheet_viewport_viewids(doc, sheet) -> Iterable[ElementId]:
    """Return the ViewIds for all Viewports placed on a sheet."""
    try:
        for vp in FilteredElementCollector(doc, sheet.Id).OfClass(Viewport):
            yield vp.ViewId
    except Exception:
        return []

__all__ = [
    "get_titleblock_instance",
    "get_sheet_size_mm",
    "sheet_paper_and_margins_mm",
    "iso_class_from_mm",
    "sheet_capacity",
    "area_from_margins",
    "clamp_area_to_margins",
    "find_sheets_by_title",
    "list_sheet_viewport_viewids",
]
