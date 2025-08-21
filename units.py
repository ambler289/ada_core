# ada_core/units.py
from Autodesk.Revit.DB import UnitUtils, UnitTypeId, SpecTypeId  # type:ignore

def mm_to_ft(mm):
    return UnitUtils.ConvertToInternalUnits(float(mm), UnitTypeId.Millimeters)

def ft_to_mm(ft):
    return UnitUtils.ConvertFromInternalUnits(float(ft), UnitTypeId.Millimeters)

def parse_float(text, default=None):
    if text is None: return default
    s = str(text).strip()
    if not s: return default
    try:
        s = s.replace(",", " ").split()[0]
        return float(s)
    except: return default

# ---- New helpers (non-breaking) ----
def is_zero_tol(a, b, tol=1e-06):
    try: return abs(float(a) - float(b)) <= float(tol)
    except: return False

def to_internal_length(value_mm):
    """Convenience alias for mm_to_ft with clearer intent."""
    return mm_to_ft(value_mm)

def to_display_mm(value_ft):
    """Alias for ft_to_mm; name mirrors intent in UI code."""
    return ft_to_mm(value_ft)

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
