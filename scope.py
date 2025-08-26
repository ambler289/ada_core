# ada_core/scope.py — generic element scope picker + grouping helpers
# Safe, dependency-light. Prefers ADa theme via ada_core.ui if present.

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    # Revit API (present under pyRevit)
    import clr
    clr.AddReference("RevitAPI")
    clr.AddReference("RevitAPIUI")
    from Autodesk.Revit import DB  # type: ignore
    from Autodesk.Revit.UI import Selection as UISelection  # type: ignore
except Exception:
    DB = None
    UISelection = None

# UI facade (theme-first, with console fallback)
try:
    from ada_core import ui as ADAUI  # your updated ada_core.ui
except Exception:
    ADAUI = None


__all__ = [
    "choose_scope", "dedupe", "collect_in_project", "collect_in_active_view",
    "is_new_construction", "group_by_host_type", "group_by_param",
]

# -----------------------------------------------------------------------------
# Tiny utilities
# -----------------------------------------------------------------------------
def _big_buttons(title: str, options: Sequence[str], message: str = "") -> Optional[str]:
    if ADAUI:
        return ADAUI.big_buttons(title=title, options=options, message=message, cancel=True)
    try:
        from pyrevit import forms as PF  # type: ignore
        rv = PF.CommandSwitchWindow.show(list(options), message=message, title=title)
        if isinstance(rv, (list, tuple)):
            return rv[0] if rv else None
        return rv
    except Exception:
        print("\n" + title)
        for i, o in enumerate(options, 1): print("{:>2}. {}".format(i, o))
        raw = input("Choose [1-{}]: ".format(len(options))).strip()
        try:
            k = int(raw);  return options[k-1]
        except Exception:
            return None

def _select_many(title: str, labels: Sequence[str]) -> Optional[List[str]]:
    if ADAUI:
        return ADAUI.select_from_list(title=title, options=list(labels), multiselect=True)
    try:
        from pyrevit import forms as PF  # type: ignore
        res = PF.SelectFromList.show(context=list(labels), title=title, multiselect=True, width=600)
        return list(res) if res is not None else None
    except Exception:
        print("\n" + title + " (comma-separated numbers, blank = cancel)")
        for i, o in enumerate(labels, 1): print("{:>2}. {}".format(i, o))
        raw = input("Select: ").strip()
        if not raw: return None
        try:
            idxs = set(int(s) for s in raw.replace(" ", "").split(",") if s)
            return [labels[i-1] for i in sorted(idxs) if 1 <= i <= len(labels)]
        except Exception:
            return None

def dedupe(elems: Iterable[Any], doc=None) -> List[Any]:
    out, seen = [], set()
    for e in elems or []:
        try:
            key = getattr(e, "UniqueId", None) or str(getattr(getattr(e, "Id", None), "IntegerValue", e))
        except Exception:
            key = str(e)
        if key in seen:  continue
        seen.add(key);  out.append(e)
    return out

# -----------------------------------------------------------------------------
# Collectors
# -----------------------------------------------------------------------------
def collect_in_project(doc, bic_or_bics, where_element_is_not_type: bool = True):
    """Collect all elements for one or more BuiltInCategory values across the project."""
    if DB is None: return []
    bics = bic_or_bics if isinstance(bic_or_bics, (list, tuple, set)) else [bic_or_bics]
    col = DB.FilteredElementCollector(doc)
    # chain categories
    filt = None
    for bic in bics:
        cat_f = DB.ElementCategoryFilter(bic)
        filt = cat_f if filt is None else DB.LogicalOrFilter(filt, cat_f)
    if filt is not None:
        col = col.WherePasses(filt)
    if where_element_is_not_type:
        col = col.WhereElementIsNotElementType()
    return list(col)

def collect_in_active_view(doc, uidoc, bic_or_bics, where_element_is_not_type: bool = True):
    if DB is None: return []
    try:
        view_id = uidoc.ActiveView.Id
    except Exception:
        return []
    bics = bic_or_bics if isinstance(bic_or_bics, (list, tuple, set)) else [bic_or_bics]
    col = DB.FilteredElementCollector(doc, view_id)
    filt = None
    for bic in bics:
        cat_f = DB.ElementCategoryFilter(bic)
        filt = cat_f if filt is None else DB.LogicalOrFilter(filt, cat_f)
    if filt is not None:
        col = col.WherePasses(filt)
    if where_element_is_not_type:
        col = col.WhereElementIsNotElementType()
    return list(col)

def is_new_construction(e) -> bool:
    try:
        p = e.LookupParameter("Phase Created")
        val = (p.AsValueString() or "").strip()
        return val == "New Construction"
    except Exception:
        return False

# -----------------------------------------------------------------------------
# Grouping helpers
# -----------------------------------------------------------------------------
def group_by_host_type(doc, elements: Sequence[Any]) -> Dict[str, List[Any]]:
    """Group hostable elements (e.g., windows/doors) by their host's Type name."""
    groups: Dict[str, List[Any]] = {}
    for el in elements or []:
        try:
            host = getattr(el, "Host", None)
            if not host: continue
            t = doc.GetElement(host.GetTypeId())
            nm = getattr(t, "Name", None) or "(Unnamed)"
        except Exception:
            nm = "(Unknown)"
        groups.setdefault(nm, []).append(el)
    return groups

def group_by_param(elements: Sequence[Any], param_name: str) -> Dict[str, List[Any]]:
    """Group elements by an instance parameter's displayed string value."""
    groups: Dict[str, List[Any]] = {}
    for el in elements or []:
        try:
            p = el.LookupParameter(param_name)
            if not p:
                key = "(No '{}')".format(param_name)
            else:
                s = (p.AsValueString() or p.AsString() or "").strip()
                key = s if s else "(empty)"
        except Exception:
            key = "(error)"
        groups.setdefault(key, []).append(el)
    return groups

# -----------------------------------------------------------------------------
# Scope chooser
# -----------------------------------------------------------------------------
def choose_scope(
    doc,
    uidoc,
    bic_or_bics,
    *,
    title: str = "Choose Scope",
    include_manual: bool = True,
    include_current_selection: bool = True,
    include_active_view: bool = True,
    include_project: bool = True,
    include_group_by_host_type: bool = False,
    filter_new_construction_for_auto: bool = True,
) -> Tuple[List[Any], str, Dict[str, Any]]:
    """
    Generic scope chooser. Returns (elements, scope_label, meta).

    - For manual & current selection we DO NOT auto-filter New Construction.
    - For active view, entire project, and group-by-host-type we DO filter
      to New Construction when `filter_new_construction_for_auto=True`.

    meta may include: {"group_by_host_type": [chosen type names]}
    """
    if DB is None:
        if ADAUI: ADAUI.alert("Revit API not available.", title=title)
        return [], "(unavailable)", {}

    choices = []
    if include_manual:             choices.append("Pick Manually")
    if include_current_selection:  choices.append("Use Current Selection")
    if include_active_view:        choices.append("Use Active View")
    if include_project:            choices.append("Use Entire Project")
    if include_group_by_host_type: choices.append("Select by Host Type")

    sel = _big_buttons(title, choices, message="")
    if not sel:
        return [], "(cancelled)", {}

    # helpers
    def _filter_nc(elems: List[Any]) -> List[Any]:
        return [e for e in elems if is_new_construction(e)] if filter_new_construction_for_auto else list(elems)

    # Use Entire Project
    if sel == "Use Entire Project":
        elems = collect_in_project(doc, bic_or_bics)
        return _filter_nc(elems), "Entire Project", {}

    # Use Active View
    if sel == "Use Active View":
        elems = collect_in_active_view(doc, uidoc, bic_or_bics)
        if not elems:
            # fall back to project
            elems = collect_in_project(doc, bic_or_bics)
            label = "Active View (fallback: Entire Project)"
        else:
            label = "Active View"
        return _filter_nc(elems), label, {}

    # Use Current Selection
    if sel == "Use Current Selection":
        try:
            ids = list(uidoc.Selection.GetElementIds())
        except Exception:
            ids = []
        elems = [doc.GetElement(i) for i in ids] if ids else []
        # filter to requested categories
        bics = bic_or_bics if isinstance(bic_or_bics, (list, tuple, set)) else [bic_or_bics]
        ok = []
        for e in elems:
            try:
                if e.Category and e.Category.Id.IntegerValue in [int(b) for b in bics]:
                    ok.append(e)
            except Exception:
                pass
        return ok, "Current Selection ({} items)".format(len(ok)), {}

    # Pick Manually
    if sel == "Pick Manually":
        class _SelFilter(UISelection.ISelectionFilter):
            def AllowElement(self, elem):
                try:
                    cat = elem.Category
                    return bool(cat and cat.Id.IntegerValue in [int(b) for b in (bic_or_bics if isinstance(bic_or_bics,(list,tuple,set)) else [bic_or_bics])])
                except Exception:
                    return False
            def AllowReference(self, ref, pt): return True
        elems = []
        # prefer multi-pick; fall back to rectangle; then none
        try:
            refs = uidoc.Selection.PickObjects(UISelection.ObjectType.Element, _SelFilter(), "Pick elements")
            elems = [doc.GetElement(r.ElementId) for r in refs]
        except Exception:
            try:
                ids = uidoc.Selection.PickElementsByRectangle(_SelFilter(), "Drag a rectangle to select")
                elems = [doc.GetElement(i) for i in ids]
            except Exception:
                elems = []
        return dedupe(elems, doc), "Picked Manually ({} items)".format(len(elems)), {}

    # Select by Host Type
    if sel == "Select by Host Type":
        elems = _filter_nc(collect_in_project(doc, bic_or_bics))
        groups = group_by_host_type(doc, elems)
        if not groups:
            return [], "(none)", {}
        labels = ["{} ({} items)".format(n, len(v)) for n, v in sorted(groups.items())]
        chosen_labels = _select_many("Select Host Type(s)", labels)
        if not chosen_labels:
            return [], "(none)", {}
        chosen_names = [lbl.split(" (", 1)[0] for lbl in chosen_labels]
        out: List[Any] = []
        for nm in chosen_names:
            out.extend(groups.get(nm, []))
        return dedupe(out, doc), "Host Type(s): " + ", ".join(chosen_names), {"group_by_host_type": chosen_names}

    # Shouldn’t reach here
    return [], "(unknown)", {}
