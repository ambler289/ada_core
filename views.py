from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ViewFamilyType, ViewFamily,
    ViewSection, View, Family, BoundingBoxXYZ, XYZ, Transform, Line,
    ElementId, BuiltInParameter, LocationPoint, ViewType
)

def section_type(doc, name):
    for vft in FilteredElementCollector(doc).OfClass(ViewFamilyType):
        if getattr(vft, "ViewFamily", None) == ViewFamily.Section and getattr(vft, "Name", None) == name:
            return vft
    return None

def view_template_id(doc, name):
    for v in FilteredElementCollector(doc).OfClass(ViewSection):
        if v.IsTemplate and v.Name == name: return v.Id
    for v in FilteredElementCollector(doc).OfClass(View):
        if v.IsTemplate and v.Name == name: return v.Id
    return None

def tag_symbol(doc, family_name):
    for fam in FilteredElementCollector(doc).OfClass(Family):
        if fam.Name == family_name:
            ids = list(fam.GetFamilySymbolIds())
            return doc.GetElement(ids[0]) if ids else None
    return None

def windows(doc, only_new=True, exclude_skylights=True):
    out=[]
    for w in (FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType()):
        if exclude_skylights and hasattr(w, "Symbol") and w.Symbol and "ADa_SKY_" in w.Symbol.Family.Name:
            continue
        if only_new:
            ph = w.LookupParameter("Phase Created")
            if not (ph and ph.AsValueString()=="New Construction"): 
                continue
        out.append(w)
    return out

def taken_view_names(doc):
    return set(v.Name.lower() for v in FilteredElementCollector(doc).OfClass(View) if not v.IsTemplate)

def unique_name(base, taken):
    i=1; name=base
    while name.lower() in taken:
        name="{}_{}".format(base,i); i+=1
    taken.add(name.lower()); return name

def create_window_section(doc, window, vft, taken, *, offset_ft, interior_ft, exterior_margin_ft,
                          base_offset_ft, extra_headroom_ft, head_ft=None):
    loc=window.Location
    if not isinstance(loc, LocationPoint): return None
    facing=window.FacingOrientation.Normalize(); origin=loc.Point; ext=facing.Negate()
    depth=offset_ft+interior_ft+exterior_margin_ft
    center=origin.Add(ext.Multiply((offset_ft-interior_ft)/2.0 + exterior_margin_ft/2.0))
    wparam = window.Symbol.LookupParameter("Width") if hasattr(window,"Symbol") else None
    width = wparam.AsDouble() if wparam else 3.0
    box_w=width+1.0
    if head_ft is None:
        hp=window.LookupParameter("Window Head Height")
        head_ft = hp.AsDouble() if hp else 6.0
    minp=XYZ(-box_w/2, -base_offset_ft, -depth/2)
    maxp=XYZ( box_w/2, head_ft+extra_headroom_ft, depth/2)
    up=XYZ.BasisZ; right=ext.CrossProduct(up).Normalize(); viewdir=ext.Negate()
    bbox=BoundingBoxXYZ(); bbox.Min=minp; bbox.Max=maxp
    xf=Transform.Identity; xf.Origin=center; xf.BasisX=right; xf.BasisY=up; xf.BasisZ=viewdir; bbox.Transform=xf
    mark=window.LookupParameter("Mark")
    base = mark.AsString() if mark and mark.AsString() else "Window_{}".format(window.Id.IntegerValue)
    name = unique_name(base, taken)
    sec=ViewSection.CreateSection(doc, vft.Id, bbox)
    if not sec: return None
    sec.Name=name
    try: sec.CropBoxActive=True
    except: pass
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
