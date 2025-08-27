# ada_core/params.py — vNext-safe parameter helpers (backward compatible)
# Keep all existing functions & signatures. Add only safe, UI-free utilities.
from __future__ import annotations

from collections import namedtuple
from typing import Optional, Tuple, Any, Union, Iterable, Sequence

# ------------------------ Existing surface (kept) ------------------------
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

# ================= vNext-safe additions (append-only) ==================
# All additions below are UI-free, defensive, and intended for reuse across tools.

from ada_core.units import ft_to_mm, mm_to_ft, parse_length_mm

# ---- Basic resolvers ----
def resolve_param(element, candidates: Union[str, Sequence[Any]], DB=None):
    """
    Try to resolve a parameter on element using a list of candidates.
    Each candidate can be:
      - string name (LookupParameter)
      - a BuiltInParameter enum (element.get_Parameter(enum)) if DB is provided
    Returns the first matching Parameter, or None.
    """
    if element is None or candidates is None:
        return None
    names: Sequence[Any] = candidates if isinstance(candidates, (list, tuple)) else [candidates]
    for c in names:
        # BuiltInParameter route
        if DB is not None:
            try:
                p = element.get_Parameter(c)
                if p: return p
            except Exception:
                pass
        # Name route
        try:
            p = element.LookupParameter(str(c))
            if p: return p
        except Exception:
            pass
    return None

def resolve_any_param(elements: Iterable, candidates: Union[str, Sequence[Any]], DB=None):
    """Return the first (element,param) where the param resolves, else (None,None)."""
    if not elements:
        return (None, None)
    for el in elements:
        p = resolve_param(el, candidates, DB=DB)
        if p:
            return (el, p)
    return (None, None)

# ---- Typed readers (tolerant) ----
def try_param_str(param) -> Optional[str]:
    try:
        if not param: return None
        s = param.AsString()
        if s is not None: return s
        # Fallback to value string for displayed values
        if hasattr(param, "AsValueString"):
            vs = param.AsValueString()
            return vs if vs not in (None, "") else None
    except Exception:
        pass
    return None

def try_param_int(param) -> Optional[int]:
    try:
        if not param: return None
        v = param.AsInteger()
        if v is not None: return int(v)
        # Parse fallback
        s = try_param_str(param)
        if s is None: return None
        s = s.strip()
        if s.lower() in ("true", "yes", "on"): return 1
        if s.lower() in ("false", "no", "off"): return 0
        return int(float(s))
    except Exception:
        return None

def try_param_double_internal(param) -> Optional[float]:
    try:
        if not param: return None
        v = param.AsDouble()
        if v is not None: return float(v)
    except Exception:
        pass
    # Fallback parse numeric token from value string
    try:
        s = try_param_str(param)
        if not s: return None
        # Extract first numeric token
        import re
        m = re.search(r"[-+]?[0-9]*\\.?[0-9]+", s)
        return float(m.group(0)) if m else None
    except Exception:
        return None

def try_param_length_mm(param) -> Optional[float]:
    """
    Return parameter value in millimetres if this is a length-like parameter.
    Tries AsDouble() → mm, then leniently parses AsValueString().
    """
    try:
        v = try_param_double_internal(param)
        if v is not None:
            return ft_to_mm(v)
    except Exception:
        pass
    try:
        s = try_param_str(param)
        return parse_length_mm(s, None)
    except Exception:
        return None

# ---- Typed writers (defensive) ----
def set_param_string(param, text: str) -> bool:
    try:
        if not param or param.IsReadOnly: return False
        return param.Set("" if text is None else str(text))
    except Exception:
        return False

def set_param_yesno(param, value_bool: bool) -> bool:
    try:
        if not param or param.IsReadOnly: return False
        # Revit stores Yes/No as integer 0/1
        return param.Set(1 if bool(value_bool) else 0)
    except Exception:
        return False

def set_param_int(param, value: int) -> bool:
    try:
        if not param or param.IsReadOnly: return False
        return param.Set(int(value))
    except Exception:
        return False

def set_param_double_internal(param, value: float) -> bool:
    try:
        if not param or param.IsReadOnly: return False
        return param.Set(float(value))
    except Exception:
        return False

def set_param_length_mm(param, value_mm: float) -> bool:
    try:
        if not param or param.IsReadOnly: return False
        return param.Set(mm_to_ft(float(value_mm)))
    except Exception:
        return False

# ---- Name-based setters (convenience) ----
def set_yesno_by_names(elem, names: Sequence[str], value_bool: bool) -> bool:
    """Try a list of parameter names on an element/type; returns True if any were set."""
    if not elem or not names:
        return False
    for nm in names:
        try:
            p = elem.LookupParameter(nm)
            if p and set_param_yesno(p, value_bool):
                return True
        except Exception:
            continue
    return False

def set_length_mm_by_names(elem, names: Sequence[str], value_mm: float) -> bool:
    if not elem or not names:
        return False
    for nm in names:
        try:
            p = elem.LookupParameter(nm)
            if p and set_param_length_mm(p, value_mm):
                return True
        except Exception:
            continue
    return False

# ---- Change-aware helpers ----
def ensure_param_length_mm(param, value_mm: float, tol_mm: float = 0.1) -> Tuple[bool, bool]:
    """
    Set length param only if different by > tol_mm.
    Returns (ok, changed).
    """
    try:
        cur = try_param_length_mm(param)
        if cur is None:
            # unknown — attempt to set
            ok = set_param_length_mm(param, value_mm)
            return (ok, ok)
        if abs(cur - float(value_mm)) <= float(tol_mm):
            return (True, False)
        ok = set_param_length_mm(param, value_mm)
        return (ok, ok)
    except Exception:
        return (False, False)

def ensure_param_int(param, value: int) -> Tuple[bool, bool]:
    try:
        cur = try_param_int(param)
        if cur is None:
            ok = set_param_int(param, value); return (ok, ok)
        if int(cur) == int(value):
            return (True, False)
        ok = set_param_int(param, value); return (ok, ok)
    except Exception:
        return (False, False)

def ensure_param_yesno(param, value_bool: bool) -> Tuple[bool, bool]:
    try:
        cur = try_param_int(param)
        target = 1 if bool(value_bool) else 0
        if cur is None:
            ok = set_param_yesno(param, value_bool); return (ok, ok)
        if int(cur) == target:
            return (True, False)
        ok = set_param_yesno(param, value_bool); return (ok, ok)
    except Exception:
        return (False, False)

# ---- Type helpers ----
def param_storage_name(param) -> str:
    try:
        return str(param.StorageType)
    except Exception:
        return "Unknown"

def is_param_readonly(param) -> bool:
    try:
        return bool(param.IsReadOnly)
    except Exception:
        return True

# ================= Version-safe TextNote write (existing addition) =================
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

__all__ = [
    # existing surface
    "ParameterSpec", "specs_from_template",
    "get_element_id_value", "read_parameter_typed", "write_parameter_typed",
    "get_parameter_element_id", "get_parameter_by_name", "has_parameter_value",
    # new resolvers & readers/writers
    "resolve_param", "resolve_any_param",
    "try_param_str", "try_param_int", "try_param_double_internal", "try_param_length_mm",
    "set_param_string", "set_param_yesno", "set_param_int", "set_param_double_internal", "set_param_length_mm",
    "set_yesno_by_names", "set_length_mm_by_names",
    "ensure_param_length_mm", "ensure_param_int", "ensure_param_yesno",
    "param_storage_name", "is_param_readonly",
    # textnote helper
    "set_textnote_text_safe",
]
