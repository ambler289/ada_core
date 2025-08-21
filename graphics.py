# -*- coding: utf-8 -*-
# ada_core/graphics.py — lightweight graphics helpers for line styles & overrides
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (
    FilteredElementCollector, LinePatternElement, BuiltInCategory, ElementId,
    OverrideGraphicSettings, GraphicsStyleType, CurveElement, DetailCurve
)
from System.Collections.Generic import List

def get_line_pattern_id(doc, name):
    try:
        for lp in FilteredElementCollector(doc).OfClass(LinePatternElement):
            if getattr(lp, "Name", None) == name:
                return lp.Id
    except Exception:
        pass
    return ElementId.InvalidElementId

def ensure_line_subcategory(doc, parent_bic, subcat_name):
    cat = doc.Settings.Categories.get_Item(parent_bic)
    subcat = None
    for sc in cat.SubCategories:
        if sc.Name == subcat_name:
            subcat = sc; break
    if not subcat:
        subcat = doc.Settings.Categories.NewSubcategory(cat, subcat_name)
    gs = subcat.GetGraphicsStyle(GraphicsStyleType.Projection)
    return subcat, gs

def apply_line_style_override(view, subcat, line_pattern_id=None, weight=1):
    ogs = OverrideGraphicSettings()
    ogs.SetProjectionLineWeight(int(weight))
    if line_pattern_id and line_pattern_id != ElementId.InvalidElementId:
        ogs.SetProjectionLinePatternId(line_pattern_id)
    view.SetCategoryOverrides(subcat.Id, ogs)

def delete_detail_curves_in_view(view, style_name):
    del_ids = List[ElementId]()
    try:
        for dc in FilteredElementCollector(view.Document, view.Id).OfClass(CurveElement):
            if isinstance(dc, DetailCurve) and getattr(dc.LineStyle, "Name", "") == style_name:
                del_ids.Add(dc.Id)
    except Exception:
        pass
    if del_ids.Count:
        view.Document.Delete(del_ids)
