# ada_core/viewsheets.py — sheet placement utilities
from Autodesk.Revit.DB import Viewport, XYZ

def place_view_on_sheet(doc, sheet, view, pt=None):
    if pt is None:
        pt = XYZ(0, 0, 0)
    return Viewport.Create(doc, sheet.Id, view.Id, pt)

def grid_layout(count, cols, cell_w, cell_h, start=None, gutter_w=0.0, gutter_h=0.0):
    """Return a list of XYZ positions for a grid with 'count' items."""
    if start is None:
        start = XYZ(0, 0, 0)
    pts = []
    for i in range(int(count)):
        r, c = divmod(i, int(cols))
        x = start.X + c * (cell_w + gutter_w)
        y = start.Y + r * (cell_h + gutter_h)
        pts.append(XYZ(x, y, 0))
    return pts
