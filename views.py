# ada_core/views.py — view helpers (backward compatible + additive)
from __future__ import annotations
from typing import Optional, Iterable, Sequence, Callable, Tuple, Set, List
import re

from Autodesk.Revit.DB import (  # type: ignore
    FilteredElementCollector, BuiltInCategory, ViewFamilyType, ViewFamily,
    ViewSection, View, Family, BoundingBoxXYZ, XYZ, Transform,
    ElementId, BuiltInParameter, LocationPoint, ViewType, ViewSheet,
    Viewport, Level, DatumEnds, ElementType
)

from ada_core.units import ft_to_mm, mm_to_ft

# ---------------------------------------------------------------------------
# Kept from working script (names/signatures preserved)
# ---------------------------------------------------------------------------

def section_type(doc, name):
    for vft in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if getattr(vft, "ViewFamily", None) == ViewFamily.Section and getattr(vft, "Name", None) == name:
            return vft
    return None


def view_template_id(doc, name):
    # Prefer section templates if caller expects section views
    for v in FilteredElementCollector(doc).OfClass(ViewSection):
        if v.IsTemplate and v.Name == name:
            return v.Id
    for v in FilteredElementCollector(doc).OfClass(View):
        if v.IsTemplate and v.Name == name:
            return v.Id
    return None


def tag_symbol(doc, family_name):
    for fam in FilteredElementCollector(doc).OfClass(Family):
        if fam.Name == family_name:
            ids = list(fam.GetFamilySymbolIds())
            return doc.GetElement(ids[0]) if ids else None
    return None


def windows(doc, only_new=True, exclude_skylights=True):
    """
    Return window instances with optional filters.
    NOTE: 'only_new' evaluates Phase Created; implementation tries ElementId route first,
          then falls back to AsValueString() for robustness across locales.
    Skylights are excluded if their family name contains 'ADa_SKY_' (customisable upstream).
    """
    out = []
    for w in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType():
        # Exclude skylights by family name pattern
        try:
            if exclude_skylights and hasattr(w, "Symbol") and w.Symbol and "ADa_SKY_" in w.Symbol.Family.Name:
                continue
        except Exception:
            pass

        # Phase filter
        if only_new:
            try:
                p = w.get_Parameter(BuiltInParameter.PHASE_CREATED)
                if p:
                    # Prefer ElementId compare if available
                    pid = p.AsElementId()
                    if isinstance(pid, ElementId) and pid != ElementId.InvalidElementId:
                        ph = doc.GetElement(pid)
                        nm = getattr(ph, "Name", None)
                        if (nm or "").strip().lower() != "new construction":
                            continue
                    else:
                        # Fallback to value string (localised)
                        vs = p.AsValueString()
                        if (vs or "").strip().lower() != "new construction":
                            continue
                else:
                    # No phase param — keep conservative
                    pass
            except Exception:
                # On any error, keep conservative: include element
                pass

        out.append(w)
    return out


def taken_view_names(doc):
    return set(v.Name.lower() for v in FilteredElementCollector(doc).OfClass(View) if not v.IsTemplate)


def unique_name(base, taken: Set[str]):
    i = 1
    name = base
    while name.lower() in taken:
        name = "{}_{}".format(base, i)
        i += 1
    taken.add(name.lower())
    return name


def create_window_section(doc, window, vft, taken, *, offset_ft, interior_ft, exterior_margin_ft,
                          base_offset_ft, extra_headroom_ft, head_ft=None):
    """
    Create a section aligned to a window's facing orientation with a parametric crop box.
    Returns the created ViewSection or None.
    """
    loc = getattr(window, "Location", None)
    if not isinstance(loc, LocationPoint):
        return None

    facing = getattr(window, "FacingOrientation", None)
    if not facing:
        return None
    try:
        facing = facing.Normalize()
    except Exception:
        return None

    origin = loc.Point
    ext = facing.Negate()

    # Depth and center of the crop in the facing axis
    depth = float(offset_ft) + float(interior_ft) + float(exterior_margin_ft)
    center = origin.Add(ext.Multiply((float(offset_ft) - float(interior_ft)) / 2.0 + float(exterior_margin_ft) / 2.0))

    # Window width
    width_ft = 3.0
    try:
        wparam = window.Symbol.LookupParameter("Width") if hasattr(window, "Symbol") and window.Symbol else None
        if wparam:
            v = wparam.AsDouble()
            if v is not None:
                width_ft = float(v)
    except Exception:
        pass
    box_w = width_ft + 1.0  # pad

    # Head height
    if head_ft is None:
        try:
            hp = window.LookupParameter("Window Head Height")
            head_ft = float(hp.AsDouble()) if hp and hp.AsDouble() is not None else 6.0
        except Exception:
            head_ft = 6.0

    # Local crop box in section space
    minp = XYZ(-box_w / 2.0, -float(base_offset_ft), -depth / 2.0)
    maxp = XYZ( box_w / 2.0,  float(head_ft) + float(extra_headroom_ft), depth / 2.0)

    up = XYZ.BasisZ
    right = ext.CrossProduct(up).Normalize()
    viewdir = ext.Negate()

    bbox = BoundingBoxXYZ()
    bbox.Min = minp
    bbox.Max = maxp

    xf = Transform.Identity
    xf.Origin = center
    xf.BasisX = right
    xf.BasisY = up
    xf.BasisZ = viewdir
    bbox.Transform = xf

    # Name from Mark or fallback
    try:
        mark = window.LookupParameter("Mark")
        base = mark.AsString() if mark and mark.AsString() else "Window_{}".format(window.Id.IntegerValue)
    except Exception:
        base = "Window_{}".format(window.Id.IntegerValue)
    name = unique_name(base, taken)

    sec = ViewSection.CreateSection(doc, vft.Id, bbox)
    if not sec:
        return None
    try:
        sec.Name = name
    except Exception:
        pass
    try:
        sec.CropBoxActive = True
    except Exception:
        pass
    return sec


# ---- New helpers (non-breaking) ----
def ensure_section_type(doc, name, fallback_first=True):
    """Return section ViewFamilyType by name, or first available if fallback_first=True."""
    vft = section_type(doc, name)
    if vft or not fallback_first:
        return vft
    for c in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if getattr(c, "ViewFamily", None) == ViewFamily.Section:
            return c
    return None


# ---------------------------------------------------------------------------
# Additive, reusable view utilities (pure / UI-free)
# ---------------------------------------------------------------------------

def collect_placed_view_ids(doc) -> Set[ElementId]:
    """Return set of View.Id that are already placed on any sheet."""
    placed = set()
    for sheet in FilteredElementCollector(doc).OfClass(ViewSheet):
        for vp in FilteredElementCollector(doc, sheet.Id).OfClass(Viewport):
            try:
                placed.add(vp.ViewId)
            except Exception:
                continue
    return placed


def named_view_predicate(suffix_regex=r'.*-D$', allowed_types=(ViewType.Section, ViewType.Elevation)) -> Callable[[View], bool]:
    """Build a predicate: non-template, allowed type, name matches regex, not starting with 'WORK'."""
    reg = re.compile(suffix_regex, re.IGNORECASE)
    def _pred(v):
        try:
            if v.IsTemplate:
                return False
            if v.ViewType not in allowed_types:
                return False
            nm = getattr(v, "Name", "") or ""
            if not reg.match(nm):
                return False
            if nm.upper().startswith("WORK"):
                return False
            return True
        except Exception:
            return False
    return _pred


def filter_unplaced_views(doc, view_predicate: Callable[[View], bool]) -> List[View]:
    """Return sorted list of views passing predicate and not yet placed (numeric-aware sort)."""
    placed = collect_placed_view_ids(doc)
    cand = []
    for v in FilteredElementCollector(doc).OfClass(View):
        try:
            if v.Id not in placed and view_predicate(v):
                cand.append(v)
        except Exception:
            continue

    def _key(v):
        nm = getattr(v, "Name", "") or ""
        try:
            head = re.split(r'[-_]', nm)[0]
            nums = re.findall(r'\d+', head)
            return (int(nums[-1]) if nums else 10**9, nm)
        except Exception:
            return (10**9, nm)

    cand.sort(key=_key)
    return cand


def estimate_paper_size_mm(view, pad_mm: float = 0.0, default_w_mm: float = 50.0, default_h_mm: float = 50.0) -> Tuple[float, float]:
    """Estimate viewport paper size from crop box and view.Scale; returns (w_mm, h_mm)."""
    try:
        scale = float(getattr(view, 'Scale', 1)) or 1.0
        cb = getattr(view, 'CropBox', None)
        if cb:
            crop_w_ft = float(cb.Max.X - cb.Min.X)
            crop_h_ft = float(cb.Max.Y - cb.Min.Y)
            paper_w_ft = crop_w_ft / scale
            paper_h_ft = crop_h_ft / scale
            w = max(20.0, ft_to_mm(paper_w_ft) + 2.0 * pad_mm)
            h = max(20.0, ft_to_mm(paper_h_ft) + 2.0 * pad_mm)
            return float(w), float(h)
    except Exception:
        pass
    return float(default_w_mm), float(default_h_mm)


def hide_level_bubbles(view, doc) -> bool:
    """Best-effort hide level bubbles in a given view."""
    try:
        levels = list(FilteredElementCollector(doc).OfClass(Level))
        for lvl in levels:
            try:
                if hasattr(lvl, "SetBubbleVisibleInView"):
                    lvl.SetBubbleVisibleInView(DatumEnds.End0, view, False)
                    lvl.SetBubbleVisibleInView(DatumEnds.End1, view, False)
                else:
                    if hasattr(lvl, "IsBubbleVisibleInView") and lvl.IsBubbleVisibleInView(DatumEnds.End0, view):
                        if hasattr(lvl, "HideBubbleInView"): lvl.HideBubbleInView(DatumEnds.End0, view)
                    if hasattr(lvl, "IsBubbleVisibleInView") and lvl.IsBubbleVisibleInView(DatumEnds.End1, view):
                        if hasattr(lvl, "HideBubbleInView"): lvl.HideBubbleInView(DatumEnds.End1, view)
            except Exception:
                continue
        return True
    except Exception:
        return False


__all__ = [
    # kept surface
    "section_type", "view_template_id", "tag_symbol",
    "windows", "taken_view_names", "unique_name", "create_window_section",
    "ensure_section_type",
    # additive utilities
    "collect_placed_view_ids", "named_view_predicate", "filter_unplaced_views",
    "estimate_paper_size_mm", "hide_level_bubbles",
]
