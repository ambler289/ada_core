import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (  # type: ignore
    BuiltInParameter, ElementId, StorageType
)

def get_level_for_elem(doc, elem):
    # quick property
    try:
        return elem.Level
    except Exception:
        pass
    # parameter "Level"
    p = elem.LookupParameter("Level")
    if p and p.StorageType == StorageType.ElementId:
        eid = p.AsElementId()
        if eid and eid != ElementId.InvalidElementId:
            lvl = doc.GetElement(eid)
            if lvl: return lvl
    # FAMILY_LEVEL_PARAM
    try:
        p = elem.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM)
        if p:
            eid = p.AsElementId()
            if eid and eid != ElementId.InvalidElementId:
                return doc.GetElement(eid)
    except Exception:
        pass
    return None

def is_existing_phase(elem):
    p = elem.LookupParameter("Phase Created")
    try:
        return bool(p and (p.AsValueString() == "Existing"))
    except Exception:
        return False

def prefix_mark_dx(elem):
    """Prefix string param 'Mark' with Dx (preserving common prefixes)."""
    p = elem.LookupParameter("Mark")
    if not p or p.IsReadOnly: 
        return False
    try:
        val = p.AsString() or ""
    except Exception:
        return False
    if val.startswith("Dx"):
        return False
    if val.startswith("Ex"):
        new_val = "Dx" + val[2:]
    elif val.startswith("D"):
        new_val = "Dx" + val[1:]
    else:
        new_val = "Dx" + val
    p.Set(new_val)
    return True
