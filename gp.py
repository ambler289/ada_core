# ada_core/gp.py — Global Parameter helpers (vNext-safe, CPython-friendly)
# Backwards-compatible: existing functions keep their names & behavior.
# Additive helpers only (won’t affect older scripts).

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional

# Revit API
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit import DB  # type: ignore


__all__ = [
    # existing API (kept)
    "ensure_gp", "set_gp_value", "get_gp_value",
    "map_global_parameters_by_name",
    "detect_global_parameter_associations",
    "dissociate_global_parameter_safely",
    "bulk_dissociate_global_parameters",
    # additive helpers (safe)
    "find_gp", "ensure_gp_by_sample",
    "set_gp_value_unit", "get_gp_value_typed",
    "associate_params_safe", "collect_gps_with_prefix",
]


# ─────────────────────────────────────────────────────────────────────────────
# Compatibility helpers (ParameterType vs ForgeTypeId)
# ─────────────────────────────────────────────────────────────────────────────
def _has_spec_utils():
    try:
        _ = DB.SpecTypeId.Number
        return True
    except Exception:
        return False


def _coerce_spec(ptype_or_spec) -> Any:
    """
    Accept either a ForgeTypeId (preferred) or a legacy ParameterType and
    return a ForgeTypeId that works with GlobalParameter.Create on newer APIs.
    """
    # If caller already passed a ForgeTypeId, keep it.
    try:
        if hasattr(ptype_or_spec, "TypeId"):   # ForgeTypeId-ish
            return ptype_or_spec
    except Exception:
        pass

    # Legacy ParameterType → best-effort map
    if not _has_spec_utils():
        # Older API path: return the legacy type as-is; Create will likely accept it.
        return ptype_or_spec

    # Minimal mapping for common kinds
    try:
        pt = ptype_or_spec
        if pt == getattr(DB.ParameterType, "Length", None):
            return DB.SpecTypeId.Length
        if pt == getattr(DB.ParameterType, "YesNo", None):
            return DB.SpecTypeId.Boolean.YesNo
        if pt == getattr(DB.ParameterType, "Angle", None):
            return DB.SpecTypeId.Angle
        if pt in (getattr(DB.ParameterType, "Integer", None),
                  getattr(DB.ParameterType, "Number",  None)):
            return DB.SpecTypeId.Number
        # default fallback
        return DB.SpecTypeId.String
    except Exception:
        return DB.SpecTypeId.String


def _mk_value_container(value, hint_spec=None):
    """Return correct DB.*ParameterValue for a python value."""
    # Boolean/YesNo
    if isinstance(value, bool):
        v = DB.IntegerParameterValue(); v.Value = 1 if value else 0; return v
    # Int
    if isinstance(value, int) and not isinstance(value, bool):
        v = DB.IntegerParameterValue(); v.Value = int(value); return v
    # Float → double
    if isinstance(value, float):
        v = DB.DoubleParameterValue(); v.Value = float(value); return v
    # ElementId (pass-through)
    if isinstance(value, DB.ElementId):
        v = DB.ElementIdParameterValue(); v.Value = value; return v
    # String (or None)
    v = DB.StringParameterValue(); v.Value = "" if value is None else str(value); return v


# ─────────────────────────────────────────────────────────────────────────────
# Find & ensure
# ─────────────────────────────────────────────────────────────────────────────
def _find_gp_internal(doc, name) -> Optional[DB.GlobalParameter]:
    try:
        eid = DB.GlobalParametersManager.FindByName(doc, name)
        if eid and eid != DB.ElementId.InvalidElementId:
            gp = doc.GetElement(eid)
            if gp and getattr(gp, "Name", None) == name:
                return gp
    except Exception:
        pass
    # Fallback scan (rarely needed but safe)
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.GlobalParameter)
        for gp in col:
            if getattr(gp, "Name", None) == name:
                return gp
    except Exception:
        pass
    return None


def find_gp(doc, name) -> Optional[DB.GlobalParameter]:
    """Public finder (safe)."""
    return _find_gp_internal(doc, name)


def ensure_gp(doc,
              name: str,
              ptype: Any = getattr(DB, "ParameterType", object) and DB.ParameterType.Text,
              group: Any = DB.BuiltInParameterGroup.PG_DATA) -> Tuple[DB.GlobalParameter, bool]:
    """
    Find a Global Parameter by name or create it.
    ptype can be legacy ParameterType or a ForgeTypeId; both accepted.
    Returns (gp, created_bool).
    """
    gp = _find_gp_internal(doc, name)
    if gp:
        return gp, False

    # Create with best-effort type coercion
    try:
        spec = _coerce_spec(ptype)
        gp = DB.GlobalParameter.Create(doc, name, spec)
    except Exception:
        # Legacy fallback: try with the raw ptype (older APIs)
        gp = DB.GlobalParameter.Create(doc, name, ptype)

    try:
        if group is not None:
            gp.GetDefinition().ParameterGroup = group
    except Exception:
        pass
    return gp, True


def ensure_gp_by_sample(doc, name: str, sample_param) -> Tuple[Optional[DB.GlobalParameter], bool]:
    """Create a GP using the sample parameter's data type. Returns (gp, created_bool)."""
    gp = _find_gp_internal(doc, name)
    if gp:
        return gp, False
    try:
        ftid = sample_param.Definition.GetDataType()
        gp = DB.GlobalParameter.Create(doc, name, ftid)
        return gp, True
    except Exception:
        return None, False


# ─────────────────────────────────────────────────────────────────────────────
# Get / set values
# ─────────────────────────────────────────────────────────────────────────────
def set_gp_value(doc,
                 name: str,
                 value: Any,
                 ptype: Any = getattr(DB, "ParameterType", object) and DB.ParameterType.Text,
                 group: Any = DB.BuiltInParameterGroup.PG_DATA) -> DB.GlobalParameter:
    """Ensure a GP then set its value. Returns the GP element."""
    gp, _ = ensure_gp(doc, name, ptype, group)
    try:
        DB.GlobalParametersManager.SetValue(doc, gp.Id, _mk_value_container(value))
    except Exception:
        try:
            gp.SetValue(_mk_value_container(value))
        except Exception:
            pass
    return gp


def set_gp_value_unit(doc, name: str, unit_tag: str, value: Any) -> DB.GlobalParameter:
    """
    Convenience setter that handles simple unit tags:
      unit_tag in {"bool","mm","deg","text"}.
    """
    if unit_tag == "bool":
        return set_gp_value(doc, name, bool(value), DB.ParameterType.YesNo, DB.BuiltInParameterGroup.PG_DATA)
    if unit_tag == "mm":
        # Caller provides mm; GP stores internal feet
        val_ft = float(value) / 304.8
        return set_gp_value(doc, name, float(val_ft), DB.ParameterType.Length, DB.BuiltInParameterGroup.PG_DATA)
    if unit_tag == "deg":
        import math
        return set_gp_value(doc, name, float(math.radians(float(value))), DB.ParameterType.Angle, DB.BuiltInParameterGroup.PG_DATA)
    # text/default
    return set_gp_value(doc, name, "" if value is None else str(value), DB.ParameterType.Text, DB.BuiltInParameterGroup.PG_DATA)


def get_gp_value(doc, name: str, default: Any = None) -> Any:
    """Return the raw stored value (int/double/string/ElementId) or default if missing."""
    gp = _find_gp_internal(doc, name)
    if not gp:
        return default
    try:
        pv = DB.GlobalParametersManager.GetValue(doc, gp.Id)
    except Exception:
        try:
            pv = gp.GetValue()
        except Exception:
            return default
    # Extract value
    try:
        if hasattr(pv, "Value"):
            return pv.Value
        if hasattr(pv, "AsString"):
            return pv.AsString()
    except Exception:
        pass
    return default


def get_gp_value_typed(doc, name: str) -> Tuple[str, Any]:
    """
    Returns (unit_tag, value) with a light inference:
      - ("bool", 0/1) for IntegerParameterValue when name suggests yes/no or value in {0,1}
      - ("mm", float) for DoubleParameterValue (assumed length)
      - ("text", str) for StringParameterValue
      - ("eid", ElementId) otherwise
    """
    gp = _find_gp_internal(doc, name)
    if not gp:
        return ("text", None)
    try:
        pv = DB.GlobalParametersManager.GetValue(doc, gp.Id)
    except Exception:
        try:
            pv = gp.GetValue()
        except Exception:
            return ("text", None)

    tname = type(pv).__name__
    if tname == "IntegerParameterValue":
        try:
            v = pv.Value
            # Treat 0/1 as bool-ish
            if v in (0, 1):
                return ("bool", v)
            return ("int", v)
        except Exception:
            return ("int", None)
    if tname == "DoubleParameterValue":
        try:
            return ("mm", float(pv.Value) * 304.8)  # display as mm
        except Exception:
            return ("num", None)
    if tname == "StringParameterValue":
        try:
            return ("text", pv.Value or "")
        except Exception:
            return ("text", None)
    if tname == "ElementIdParameterValue":
        try:
            return ("eid", pv.Value)
        except Exception:
            return ("eid", None)
    return ("text", None)


# ─────────────────────────────────────────────────────────────────────────────
# Mapping / discovery
# ─────────────────────────────────────────────────────────────────────────────
def map_global_parameters_by_name(doc) -> Dict[str, DB.GlobalParameter]:
    """Build a name → GlobalParameter map."""
    m = {}
    try:
        for gp in DB.FilteredElementCollector(doc).OfClass(DB.GlobalParameter):
            m[getattr(gp, "Name", "")] = gp
    except Exception:
        pass
    return m


def collect_gps_with_prefix(doc, prefix: str) -> List[DB.GlobalParameter]:
    """Return all GPs whose names start with `prefix`."""
    res = []
    try:
        for gp in DB.FilteredElementCollector(doc).OfClass(DB.GlobalParameter):
            nm = getattr(gp, "Name", "") or ""
            if nm.startswith(prefix):
                res.append(gp)
    except Exception:
        pass
    return res


# ─────────────────────────────────────────────────────────────────────────────
# Association detection / removal
# ─────────────────────────────────────────────────────────────────────────────
def detect_global_parameter_associations(elements: List, doc) -> List[Dict[str, Any]]:
    """
    Detect GP associations for a list of elements.
    Returns a list of dicts: {elem, param, gp_id, method, gp_name}
    """
    try:
        from ada_core.params import get_element_id_value  # optional
    except Exception:
        def get_element_id_value(element_id):
            try:
                if hasattr(element_id, 'IntegerValue'):
                    return element_id.IntegerValue
                elif hasattr(element_id, 'Value'):
                    return element_id.Value
                else:
                    return int(str(element_id))
            except Exception:
                return str(element_id)

    gp_map = map_global_parameters_by_name(doc)
    found = []
    for el in elements or []:
        try:
            for p in el.Parameters:
                pname = p.Definition.Name
                # Primary: API association
                gid = None
                try:
                    if hasattr(p, "GetAssociatedGlobalParameter"):
                        tmp = p.GetAssociatedGlobalParameter()
                        if isinstance(tmp, DB.ElementId) and get_element_id_value(tmp) != -1:
                            gid = tmp
                except Exception:
                    gid = None
                if gid:
                    gp_elem = doc.GetElement(gid)
                    gname = getattr(gp_elem, "Name", None)
                    found.append({"elem": el, "param": p, "gp_id": gid, "method": "Associated", "gp_name": gname})
                    continue
                # Secondary: name match (param name == GP name)
                if pname in gp_map:
                    found.append({"elem": el, "param": p, "gp_id": gp_map[pname].Id, "method": "NameMatch", "gp_name": pname})
        except Exception:
            continue
    return found


def dissociate_global_parameter_safely(entry: Dict[str, Any], doc) -> Tuple[bool, str]:
    """
    Safely dissociate a GP from a parameter while preserving the current parameter value.
    `entry` is an item from detect_global_parameter_associations().
    """
    try:
        from ada_core.params import read_parameter_typed, write_parameter_typed, get_parameter_element_id  # optional
    except Exception:
        def read_parameter_typed(param, DB=None):
            try:
                st = getattr(param, "StorageType", None)
                if str(st) == "Double":    return ("double", param.AsDouble())
                if str(st) == "Integer":   return ("int",    param.AsInteger())
                if str(st) == "String":    return ("str",    param.AsString())
                if str(st) == "ElementId": return ("id",     param.AsElementId())
            except Exception:
                pass
            return (None, None)
        def write_parameter_typed(param, value_info):
            try:
                vt, v = value_info
                return param.Set(v) if vt is not None else False
            except Exception:
                return False
        def get_parameter_element_id(param, DB=None):
            try:
                return getattr(param, "Id", None)
            except Exception:
                return None

    el = entry["elem"]; p = entry["param"]
    value_info = read_parameter_typed(p)

    pid = get_parameter_element_id(p)
    if pid:
        try:
            DB.GlobalParametersManager.DissociateGlobalParameter(doc, el.Id, pid)
            if not getattr(p, "IsReadOnly", True) and value_info[0] is not None:
                write_parameter_typed(p, value_info)
            return True, "GlobalParametersManager"
        except Exception:
            pass

    try:
        if hasattr(p, "DissociateFromGlobalParameter"):
            p.DissociateFromGlobalParameter()
            if not getattr(p, "IsReadOnly", True) and value_info[0] is not None:
                write_parameter_typed(p, value_info)
            return True, "ParameterAPI"
    except Exception:
        pass
    return False, "Failed"


def bulk_dissociate_global_parameters(associations: List[Dict[str, Any]], doc) -> Tuple[int, int]:
    """Bulk-dissociate GP associations; returns (removed, failed)."""
    removed, failed = 0, 0
    tg = DB.TransactionGroup(doc, "Bulk Remove Global Parameter Associations")
    tg.Start()
    for entry in associations:
        t = None
        try:
            pname = entry["param"].Definition.Name
            t = DB.Transaction(doc, "Dissociate: " + pname); t.Start()
            ok, _m = dissociate_global_parameter_safely(entry, doc)
            if ok:
                t.Commit(); removed += 1
            else:
                if t and t.GetStatus() == DB.TransactionStatus.Started: t.RollBack()
                failed += 1
        except Exception:
            try:
                if t and t.GetStatus() == DB.TransactionStatus.Started: t.RollBack()
            except Exception:
                pass
            failed += 1
    try:
        tg.Assimilate()
    except Exception:
        tg.RollBack(); return 0, len(associations)
    return removed, failed


# ─────────────────────────────────────────────────────────────────────────────
# Safe association helper (additive)
# ─────────────────────────────────────────────────────────────────────────────
def associate_params_safe(elements, inst_to_gp_map: Dict[str, str], gp_ids: Dict[str, DB.ElementId]) -> Tuple[int, List[str]]:
    """
    Associate instance parameters to GPs by name.
    inst_to_gp_map: {"Instance Param Name": "Global Parameter Name"}
    gp_ids:         {"Global Parameter Name": ElementId}
    Returns (total_associated, logs)
    """
    n = 0; logs = []
    for inst_name, gp_name in (inst_to_gp_map or {}).items():
        gid = gp_ids.get(gp_name)
        if not gid:
            logs.append("Missing GP: {}".format(gp_name)); continue
        count = 0
        for el in elements or []:
            try:
                p = el.LookupParameter(inst_name)
                if p and p.CanBeAssociatedWithGlobalParameter(gid):
                    p.AssociateWithGlobalParameter(gid); n += 1; count += 1
            except Exception as e:
                logs.append("Failed {} on {}: {}".format(inst_name, el.Id, e))
        if count:
            logs.append("Associated '{}' → '{}' on {} elements".format(inst_name, gp_name, count))
    return n, logs
