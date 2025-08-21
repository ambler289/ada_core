# ada_core/gp.py — Global Parameter helpers (Revit 2025+), CPython-safe
from typing import List, Dict, Any, Tuple
from Autodesk.Revit.DB import (  # type:ignore
    GlobalParametersManager,
    GlobalParameter,
    ElementId,
    DoubleParameterValue,
    IntegerParameterValue,
    StringParameterValue,
    BuiltInParameterGroup,
    ParameterType,
    FilteredElementCollector,
)

__all__ = [
    "ensure_gp", "set_gp_value", "get_gp_value",
    "map_global_parameters_by_name",
    "detect_global_parameter_associations",
    "dissociate_global_parameter_safely",
    "bulk_dissociate_global_parameters",
]

def _find_gp(doc, name):
    eid = GlobalParametersManager.FindByName(doc, name)
    if eid and eid != ElementId.InvalidElementId:
        gp = doc.GetElement(eid)
        if gp and gp.Name == name:
            return gp
    for eid in GlobalParametersManager.GetAllGlobalParameters(doc):
        gp = doc.GetElement(eid)
        if gp and gp.Name == name:
            return gp
    return None

def ensure_gp(doc, name, ptype=ParameterType.Text, group=BuiltInParameterGroup.PG_DATA):
    """Find a Global Parameter by name or create it. Returns (gp, created_bool)."""
    gp = _find_gp(doc, name)
    if gp:
        return gp, False
    gp = GlobalParameter.Create(doc, name, ptype)
    try:
        if group is not None:
            gp.GetDefinition().ParameterGroup = group
    except Exception:
        pass
    return gp, True

def set_gp_value(doc, name, value, ptype=ParameterType.Text, group=BuiltInParameterGroup.PG_DATA):
    """Create/ensure GP then set value using the correct value container."""
    gp, _ = ensure_gp(doc, name, ptype, group)
    if ptype in (ParameterType.Length, ParameterType.Number) or isinstance(value, float):
        v = DoubleParameterValue(float(value))
    elif ptype in (ParameterType.Integer, ParameterType.YesNo) or isinstance(value, (int, bool)):
        v = IntegerParameterValue(int(bool(value)) if ptype == ParameterType.YesNo else int(value))
    else:
        v = StringParameterValue("" if value is None else str(value))
    GlobalParametersManager.SetValue(doc, gp.Id, v)
    return gp

def get_gp_value(doc, name, default=None):
    gp = _find_gp(doc, name)
    if not gp:
        return default
    try:
        pv = GlobalParametersManager.GetValue(doc, gp.Id)
        if hasattr(pv, "Value"):
            return pv.Value
        if hasattr(pv, "AsString"):
            return pv.AsString()
        return default
    except Exception:
        return default

def map_global_parameters_by_name(doc) -> Dict[str, Any]:
    """Create efficient name->GlobalParameter mapping for lookups."""
    global_params = {}
    try:
        for gp in FilteredElementCollector(doc).OfClass(GlobalParameter):
            global_params[gp.Name] = gp
    except Exception:
        pass
    return global_params

def detect_global_parameter_associations(elements: List, doc) -> List[Dict[str, Any]]:
    """Detect GP associations using API handles and name matching."""
    try:
        from ada_core.params import get_element_id_value
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

    global_params = map_global_parameters_by_name(doc)
    found = []
    for element in elements:
        try:
            for param in element.Parameters:
                param_name = param.Definition.Name
                gp_id = None
                try:
                    if hasattr(param, "GetAssociatedGlobalParameter"):
                        gid = param.GetAssociatedGlobalParameter()
                        if isinstance(gid, ElementId) and get_element_id_value(gid) != -1:
                            gp_id = gid
                except Exception:
                    pass

                if gp_id:
                    gp_element = doc.GetElement(gp_id)
                    gp_name = gp_element.Name if gp_element else None
                    found.append({"elem": element, "param": param, "gp_id": gp_id, "method": "Associated", "gp_name": gp_name})
                    continue

                if param_name in global_params:
                    found.append({"elem": element, "param": param, "gp_id": global_params[param_name].Id, "method": "NameMatch", "gp_name": param_name})
        except Exception:
            continue
    return found

def dissociate_global_parameter_safely(entry: Dict[str, Any], doc) -> Tuple[bool, str]:
    """Safely dissociate GP while preserving parameter value."""
    try:
        from ada_core.params import read_parameter_typed, write_parameter_typed, get_parameter_element_id
    except Exception:
        def read_parameter_typed(param, DB=None):
            try:
                if hasattr(param, 'StorageType'):
                    st = param.StorageType
                    if str(st) == "Double": return ("double", param.AsDouble())
                    elif str(st) == "Integer": return ("int", param.AsInteger())
                    elif str(st) == "String": return ("str", param.AsString())
                    elif str(st) == "ElementId": return ("id", param.AsElementId())
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
                pid = getattr(param, "Id", None)
                if pid: return pid
            except Exception:
                pass
            return None

    element = entry["elem"]
    param = entry["param"]
    value_info = read_parameter_typed(param)

    param_id = get_parameter_element_id(param)
    if param_id:
        try:
            GlobalParametersManager.DissociateGlobalParameter(doc, element.Id, param_id)
            if not param.IsReadOnly and value_info[0] is not None:
                write_parameter_typed(param, value_info)
            return True, "GlobalParametersManager"
        except Exception:
            pass

    try:
        if hasattr(param, "DissociateFromGlobalParameter"):
            param.DissociateFromGlobalParameter()
            if not param.IsReadOnly and value_info[0] is not None:
                write_parameter_typed(param, value_info)
            return True, "ParameterAPI"
    except Exception:
        pass
    return False, "Failed"

def bulk_dissociate_global_parameters(associations: List[Dict[str, Any]], doc) -> Tuple[int, int]:
    """Bulk dissociate GP associations; returns (removed, failed)."""
    from Autodesk.Revit.DB import Transaction, TransactionGroup, TransactionStatus  # type:ignore
    removed, failed = 0, 0
    tg = TransactionGroup(doc, "Bulk Remove Global Parameter Associations")
    tg.Start()
    for entry in associations:
        t = None
        try:
            pname = entry["param"].Definition.Name
            t = Transaction(doc, "Dissociate: " + pname); t.Start()
            ok, _m = dissociate_global_parameter_safely(entry, doc)
            if ok:
                t.Commit(); removed += 1
            else:
                if t and t.GetStatus() == TransactionStatus.Started: t.RollBack()
                failed += 1
        except Exception:
            try:
                if t and t.GetStatus() == TransactionStatus.Started: t.RollBack()
            except Exception:
                pass
            failed += 1
    try:
        tg.Assimilate()
    except Exception:
        tg.RollBack(); return 0, len(associations)
    return removed, failed

# ================= vNext safe additions (append-only) ==================
# Global Parameter helpers that won't collide with existing names.

def gp_spec_id_safe(kind, DB):
    """Resolve common spec kinds to ForgeTypeId across API variants."""
    try:
        if kind == "Number":  return DB.SpecTypeId.Number
        if kind == "YesNo":   return DB.SpecTypeId.Boolean.YesNo
        if kind == "Length":  return DB.SpecTypeId.Length
        if kind == "Angle":   return DB.SpecTypeId.Angle
    except Exception:
        pass
    return DB.SpecTypeId.Number  # safe default

def create_or_find_gp_safe(doc, name, kind, default=None, group=None):
    """Create or fetch a Global Parameter by name. Returns (ElementId, created_bool)."""
    from Autodesk.Revit import DB  # type: ignore
    gid = DB.GlobalParametersManager.FindByName(doc, name)
    if gid != DB.ElementId.InvalidElementId:
        return gid, False
    try:
        ftid = gp_spec_id_safe(kind, DB)
        gp = DB.GlobalParameter.Create(doc, name, ftid)
        try:
            if group is not None:
                gp.GetDefinition().ParameterGroup = group
        except Exception:
            pass
        if default is not None:
            try:
                if kind == "YesNo":
                    v = DB.IntegerParameterValue(); v.Value = int(bool(default))
                else:
                    v = DB.DoubleParameterValue();  v.Value = float(default)
                gp.SetValue(v)
            except Exception:
                pass
        return gp.Id, True
    except Exception:
        return None, False

def create_legacy_gp_from_param_safe(doc, name, sample_param):
    """Create a GP using data type from an existing parameter. Returns (ElementId, created_bool)."""
    from Autodesk.Revit import DB  # type: ignore
    try:
        ftid = sample_param.Definition.GetDataType()
        if not DB.SpecUtils.IsSpec(ftid):
            return None, False
        gp = DB.GlobalParameter.Create(doc, name, ftid)
        return gp.Id, True
    except Exception:
        return None, False

def associate_params_safe(elements, inst_to_gp_map, gp_ids):
    """Associate instance parameters to GPs. Returns (count, logs)."""
    from Autodesk.Revit import DB  # type: ignore
    n = 0; logs = []
    for inst_name, gp_name in (inst_to_gp_map or {}).items():
        gid = gp_ids.get(gp_name)
        if not gid:
            logs.append("Missing GP: {}".format(gp_name)); continue
        count = 0
        for el in elements or []:
            p = el.LookupParameter(inst_name)
            if p and p.CanBeAssociatedWithGlobalParameter(gid):
                try:
                    p.AssociateWithGlobalParameter(gid); n += 1; count += 1
                except Exception as e:
                    logs.append("Failed {} on {}: {}".format(inst_name, el.Id, e))
        if count:
            logs.append("Associated '{}' → '{}' on {} elements".format(inst_name, gp_name, count))
    return n, logs
