import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import BuiltInParameter  # type: ignore

def is_ground_level(level):
    """Matches 'ground', 'level 0', 'l0', 'grade' or ~0 elevation."""
    try:
        try:
            level_name = (level.Name or "").lower()
        except Exception:
            name_param = level.get_Parameter(BuiltInParameter.DATUM_TEXT)
            level_name = (name_param.AsString() or "").lower() if name_param else ""
        elev = getattr(level, "Elevation", None)
        if any(p in level_name for p in ("ground", "level 0", "level 00", "l0", "l00", "grade")):
            return True
        if elev is not None and abs(elev) < 1.0:
            return True
    except Exception:
        pass
    return False
