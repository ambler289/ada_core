import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (  # type: ignore
    FilteredElementCollector, BuiltInCategory, BuiltInParameter
)

def find_type_by_name_and_family(doc, type_name, family_name):
    types = (FilteredElementCollector(doc)
             .OfCategory(BuiltInCategory.OST_Doors)
             .WhereElementIsElementType()
             .ToElements())
    for t in types:
        try:
            if t.Name == type_name and t.Family.Name == family_name:
                return t
        except Exception:
            try:
                n = t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
                if n and n.AsString() == type_name and t.Family.Name == family_name:
                    return t
            except Exception:
                pass
    return None

def duplicate_type_with_name(orig_type, new_name):
    return orig_type.Duplicate(new_name)
