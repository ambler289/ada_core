# -*- coding: utf-8 -*-
# ada_core/roofs.py — roof selection & outline extraction
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (
    Options, GeometryInstance, Solid, FootPrintRoof, XYZ, BoundingBoxXYZ,
    DetailCurve, Line, ViewPlan
)
from Autodesk.Revit.UI.Selection import ObjectType

import System
import numpy as _np

def pick_roofs(uidoc, prompt="Select roof(s) to outline"):
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, prompt)
        return [uidoc.Document.GetElement(r.ElementId) for r in refs]
    except System.Exception:
        return []

def roof_profile_curves(roof):
    """Try to pull explicit footprint profiles (fast path)."""
    if isinstance(roof, FootPrintRoof):
        try:
            raw = roof.GetProfiles()  # IList<ModelCurveArray>
            for arr in raw:
                for mc in arr:
                    yield mc.GeometryCurve
            return
        except Exception:
            pass

def _slice_solid_edges_at_z(solid, z, tol=0.01):
    for e in solid.Edges:
        try:
            crv = e.AsCurve()
            pts = crv.Tessellate()
            arr = _np.array([[p.X, p.Y, p.Z] for p in pts], dtype=float)
            if _np.allclose(arr[:,2], z, atol=tol):
                yield crv
        except Exception:
            continue

def slice_roof_at_z(roof, z, tol=0.01):
    opt = Options(); opt.ComputeReferences = True
    geom = roof.get_Geometry(opt)
    for obj in geom:
        items = obj.GetInstanceGeometry() if isinstance(obj, GeometryInstance) else [obj]
        for it in items:
            if isinstance(it, Solid) and it.Volume > 0:
                for crv in _slice_solid_edges_at_z(it, z, tol):
                    yield crv
