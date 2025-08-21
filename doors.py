import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import BuiltInParameter, StorageType  # type: ignore

def get_panel_width_mm(door_type):
    p = door_type.LookupParameter("Panel Width")
    if p and p.StorageType == StorageType.Double:
        return int(round(p.AsDouble() * 304.8))
    return None

def set_panel_height_ft(door_type, height_ft):
    p = door_type.LookupParameter("Panel Height")
    if p and not p.IsReadOnly:
        p.Set(float(height_ft))
        return True
    return False
