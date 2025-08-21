# ada_core/geom.py — minimal geometry helpers
from Autodesk.Revit.DB import BoundingBoxXYZ, Transform, XYZ

def bbox_from_elements(elements, expand=0.0):
    mins, maxs = [], []
    for e in elements or []:
        bb = e.get_BoundingBox(None)
        if not bb:
            continue
        mins.append(bb.Min); maxs.append(bb.Max)
    if not mins:
        return None
    minx = min(p.X for p in mins) - expand
    miny = min(p.Y for p in mins) - expand
    minz = min(p.Z for p in mins) - expand
    maxx = max(p.X for p in maxs) + expand
    maxy = max(p.Y for p in maxs) + expand
    maxz = max(p.Z for p in maxs) + expand
    bb = BoundingBoxXYZ()
    bb.Min = XYZ(minx, miny, minz)
    bb.Max = XYZ(maxx, maxy, maxz)
    return bb

def line_overlap_1d(a0, a1, b0, b1, tol=1e-9):
    lo = max(min(a0, a1), min(b0, b1))
    hi = min(max(a0, a1), max(b0, b1))
    return max(0.0, hi - lo) if (hi - lo) > tol else 0.0
