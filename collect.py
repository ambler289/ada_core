# ada_core/collect.py
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter, Element

def _is_new_construction(elem: Element):
    try:
        ph = elem.get_Parameter(BuiltInParameter.PHASE_CREATED).AsElementId()
        return ph.IntegerValue >= 0  # keep existing semantics
    except: return True

def windows_new_construction(doc, predicate=None):
    elems = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).ToElements()
    out = [e for e in elems if _is_new_construction(e)]
    return [e for e in out if (predicate(e) if predicate else True)]

def windows_in_view(doc, view, predicate=None):
    ids = view.GetElementIds()
    out = []
    for e in (doc.GetElement(i) for i in ids):
        if e and e.Category and e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Windows):
            if _is_new_construction(e) and (predicate(e) if predicate else True):
                out.append(e)
    return out

# ---- New helpers (non-breaking) ----
def instances_of(doc, bic):
    """Generic instance collector by BuiltInCategory."""
    return list(FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType())

def types_of(doc, bic):
    """Generic type collector by BuiltInCategory."""
    return list(FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType())

# Generic "collect by scope" pattern (category + optional predicate).

def collect_by_scope_safe(doc, view, bic, scope_label, predicate=None):
    """Return (elements, scope_str) filtered by category and optional predicate."""
    from Autodesk.Revit import DB  # type: ignore
    if "Active View" in str(scope_label) and hasattr(view, "Id"):
        fec = DB.FilteredElementCollector(doc, view.Id)
        scope = "active view ({})".format(getattr(view, "Name", "View"))
    else:
        fec = DB.FilteredElementCollector(doc)
        scope = "entire project"
    elems = list(fec.OfCategory(bic).WhereElementIsNotElementType().ToElements())
    if predicate:
        try:
            elems = [e for e in elems if predicate(e)]
        except Exception:
            pass
    return elems, scope
