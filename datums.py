
from Autodesk.Revit.DB import (FilteredElementCollector, BuiltInCategory, ElementId,
    DatumEnds, DatumExtentType, XYZ, Line, BuiltInParameter, ViewType)

def _scope_param(view):
    for bipn in ("VIEWER_VOLUME_OF_INTEREST_CROP","VIEWER_VOLUME_OF_INTEREST"):
        bip=getattr(BuiltInParameter,bipn,None)
        if bip:
            p=view.get_Parameter(bip)
            if p: return p
    return view.LookupParameter("Scope Box")

def _curve_in_view(lvl, view):
    try: crvs=lvl.GetCurvesInView(DatumExtentType.ViewSpecific, view)
    except: crvs=None
    if not crvs or crvs.Count==0:
        try: crvs=lvl.GetCurvesInView(DatumExtentType.Model, view)
        except: crvs=None
        if not crvs or crvs.Count==0: return None
    return crvs[0]

def force_hide_level_bubbles(doc, view, pad_ft):
    if getattr(view,"ViewType",None) not in (ViewType.Section, ViewType.Elevation): return
    try:
        if view.GetCategoryHidden(ElementId(BuiltInCategory.OST_Levels)): return
    except: pass
    sp=_scope_param(view); saved=None
    if sp and not sp.IsReadOnly:
        try:
            saved=sp.AsElementId()
            if saved and saved!=ElementId.InvalidElementId: sp.Set(ElementId.InvalidElementId)
        except: pass
    doc.Regenerate()
    try:
        bbox=view.CropBox
        if bbox:
            xf=bbox.Transform; inv=xf.Inverse
            levels=(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Levels)
                    .WhereElementIsNotElementType())
            for lvl in levels:
                try:
                    crv=_curve_in_view(lvl,view)
                    if crv is None: continue
                    for end in (DatumEnds.End0, DatumEnds.End1):
                        try: lvl.SetDatumExtentType(end, view, DatumExtentType.ViewSpecific)
                        except: pass
                    p0=inv.OfPoint(crv.GetEndPoint(0)); p1=inv.OfPoint(crv.GetEndPoint(1))
                    y=0.5*(p0.Y+p1.Y); z=0.5*(p0.Z+p1.Z)
                    pL=xf.OfPoint(XYZ(bbox.Min.X - pad_ft, y, z))
                    pR=xf.OfPoint(XYZ(bbox.Max.X + pad_ft, y, z))
                    lvl.SetCurveInView(DatumExtentType.ViewSpecific, view, Line.CreateBound(pL,pR))
                except: pass
        doc.Regenerate()
        # hide heads
        levels=(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Levels)
                .WhereElementIsNotElementType())
        for lvl in levels:
            crv=_curve_in_view(lvl,view)
            if crv is None: continue
            for end in (DatumEnds.End0, DatumEnds.End1):
                try: lvl.SetDatumExtentType(end, view, DatumExtentType.ViewSpecific)
                except: pass
                try: lvl.HideBubbleInView(end, view)
                except:
                    try: doc.Regenerate(); lvl.HideBubbleInView(end, view)
                    except: pass
        doc.Regenerate()
    finally:
        if sp and saved is not None:
            try: sp.Set(saved)
            except: pass
        doc.Regenerate()
