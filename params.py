# ada_core/params.py
from collections import namedtuple
from typing import Optional, Tuple, Any, Union

ParameterSpec = namedtuple("ParameterSpec", "name display ptype unit default notes is_editable")

def specs_from_template(template_data):
    editable = [
        ("Window Head Height", "Window Head Height", "float", "mm"),
        ("Frame Setback", "Frame Setback", "float", "mm"),
        ("Ext Sill Show", "Ext Sill Show", "bool", ""),
        ("Ext Trim Show", "Ext Trim Show", "bool", "")
    ]
    specs = []
    cfg = template_data.get("window_parameters", {})
    for key, disp, ptype, unit in editable:
        meta = cfg.get(key, {})
        specs.append(ParameterSpec(
            name=key, display=meta.get("display_name", disp),
            ptype=ptype, unit=meta.get("unit", unit),
            default=meta.get("default_value", None),
            notes=meta.get("notes", ""),
            is_editable=True
        ))
    return specs

# ---- Additional Parameter Utilities (kept BC) ----
def get_element_id_value(element_id) -> Union[int, str]:
    try:
        if hasattr(element_id, 'IntegerValue'):
            return element_id.IntegerValue
        elif hasattr(element_id, 'Value'):
            return element_id.Value
        else:
            return int(str(element_id))
    except Exception:
        return str(element_id)

def read_parameter_typed(param, DB) -> Tuple[Optional[str], Any]:
    try:
        st = param.StorageType
        if st == DB.StorageType.Double:    return ("double", param.AsDouble())
        if st == DB.StorageType.Integer:   return ("int",    param.AsInteger())
        if st == DB.StorageType.String:    return ("str",    param.AsString())
        if st == DB.StorageType.ElementId: return ("id",     param.AsElementId())
    except Exception:
        pass
    return (None, None)

def write_parameter_typed(param, value_info: Tuple[Optional[str], Any]) -> bool:
    try:
        vt, v = value_info
        if vt is None: return False
        return param.Set(v)
    except Exception:
        return False

def get_parameter_element_id(param, DB):
    try:
        pid = getattr(param, "Id", None)
        if isinstance(pid, DB.ElementId) and get_element_id_value(pid) != -1:
            return pid
    except Exception:
        pass
    try:
        definition = param.Definition
        if hasattr(definition, "BuiltInParameter"):
            bip = definition.BuiltInParameter
            if bip != DB.BuiltInParameter.INVALID:
                return DB.ElementId(bip)
    except Exception:
        pass
    return None

def get_parameter_by_name(element, param_name: str, DB=None):
    try:
        return element.LookupParameter(param_name)
    except Exception:
        return None

def has_parameter_value(param) -> bool:
    try:
        if not param or param.IsReadOnly:
            return False
        st = param.StorageType
        if hasattr(param, 'HasValue') and not param.HasValue:
            return False
        if str(st) == "Double":    return param.AsDouble() is not None
        if str(st) == "Integer":   return param.AsInteger() is not None
        if str(st) == "String":
            val = param.AsString()
            return val is not None and val.strip() != ""
        if str(st) == "ElementId":
            eid = param.AsElementId()
            return eid is not None and get_element_id_value(eid) != -1
    except Exception:
        pass
    return False

# ================= vNext safe additions (append-only) ==================
# Version-safe TextNote write without clobbering existing functions.

def set_textnote_text_safe(tn, text, DB):
    """Set TextNote text via TEXT_TEXT; falls back to SetText if available. Returns bool."""
    try:
        p = tn.get_Parameter(DB.BuiltInParameter.TEXT_TEXT)
        if p and not p.IsReadOnly:
            p.Set(text)
            return True
    except Exception:
        pass
    try:
        if hasattr(tn, "SetText"):
            tn.SetText(text)
            return True
    except Exception:
        pass
    return False
