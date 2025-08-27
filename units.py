# ada_core/units.py — vNext-safe units + tiny GP utilities
# Backwards-compatible: existing functions keep behavior/signatures.
# Additive helpers only (won’t break older scripts).
from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Tuple

# ---------------- Revit Units compatibility (old/new API) ----------------
try:
    # Revit 2021+ (new Units API)
    from Autodesk.Revit.DB import UnitUtils, UnitTypeId, SpecTypeId  # type: ignore
    _HAS_NEW_UNITS = True
except Exception:
    # Older API fallback
    from Autodesk.Revit.DB import UnitUtils  # type: ignore
    try:
        from Autodesk.Revit.DB import DisplayUnitType  # type: ignore
    except Exception:
        DisplayUnitType = None  # type: ignore
    UnitTypeId = None  # type: ignore
    SpecTypeId = None  # type: ignore
    _HAS_NEW_UNITS = False

# ---------------- Constants ----------------
MM_PER_FT: float = 304.8
FT_PER_MM: float = 1.0 / MM_PER_FT

# ---------------- Core conversions (kept; behavior-compatible) ----------------
def mm_to_ft(mm: float) -> float:
    """Millimetres → internal feet."""
    if _HAS_NEW_UNITS:
        return UnitUtils.ConvertToInternalUnits(float(mm), UnitTypeId.Millimeters)
    # Legacy fallback
    if 'DisplayUnitType' in globals() and DisplayUnitType is not None:
        return UnitUtils.ConvertToInternalUnits(float(mm), DisplayUnitType.DUT_MILLIMETERS)
    # Last resort
    return float(mm) * FT_PER_MM


def ft_to_mm(ft: float) -> float:
    """Internal feet → millimetres."""
    if _HAS_NEW_UNITS:
        return UnitUtils.ConvertFromInternalUnits(float(ft), UnitTypeId.Millimeters)
    # Legacy fallback
    if 'DisplayUnitType' in globals() and DisplayUnitType is not None:
        return UnitUtils.ConvertFromInternalUnits(float(ft), DisplayUnitType.DUT_MILLIMETERS)
    # Last resort
    return float(ft) * MM_PER_FT


def parse_float(text: Any, default: Optional[float] = None) -> Optional[float]:
    if text is None:
        return default
    s = str(text).strip()
    if not s:
        return default
    try:
        s = s.replace(",", " ").split()[0]
        return float(s)
    except Exception:
        return default


# ---- Existing lightweight helpers (kept) ----
def is_zero_tol(a: float, b: float, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= float(tol)
    except Exception:
        return False


def to_internal_length(value_mm: float) -> float:
    """Alias for mm_to_ft (semantic clarity in call-sites)."""
    return mm_to_ft(value_mm)


def to_display_mm(value_ft: float) -> float:
    """Alias for ft_to_mm (semantic clarity in call-sites)."""
    return ft_to_mm(value_ft)


# ================= vNext-safe additions (append-only) ==================

# ---- Math/utility helpers ----
def clamp(x: float, lo: float, hi: float) -> float:
    try:
        xf = float(x)
        return lo if xf < lo else hi if xf > hi else xf
    except Exception:
        return x

def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)

def round_mm(value_ft: float, step_mm: float = 1.0) -> float:
    """Round a length in feet to the nearest *step_mm* in mm, returning mm."""
    mm = ft_to_mm(value_ft)
    if step_mm <= 0:
        return mm
    return round(mm / step_mm) * step_mm

def floor_mm(value_ft: float, step_mm: float = 1.0) -> float:
    mm = ft_to_mm(value_ft)
    if step_mm <= 0:
        return mm
    return math.floor(mm / step_mm) * step_mm #type:ignore

def ceil_mm(value_ft: float, step_mm: float = 1.0) -> float:
    mm = ft_to_mm(value_ft)
    if step_mm <= 0:
        return mm
    return math.ceil(mm / step_mm) * step_mm #type:ignore

# ---- Angles & general converters ----
def deg_to_rad(deg: float) -> float:
    import math
    return math.radians(float(deg))


def rad_to_deg(rad: float) -> float:
    import math
    return math.degrees(float(rad))


def to_internal(value: Any, unit_tag: str) -> Any:
    """
    Convert a UI/display value into Revit internal storage:
      unit_tag in {"mm","cm","m","deg","bool","text"}.
    """
    ut = (unit_tag or "").lower()
    if ut == "mm":
        return mm_to_ft(float(value))
    if ut == "cm":
        return mm_to_ft(float(value) * 10.0)
    if ut == "m":
        return mm_to_ft(float(value) * 1000.0)
    if ut == "deg":
        return deg_to_rad(float(value))
    if ut == "bool":
        return bool(value)
    # text / passthrough
    return "" if value is None else str(value)


def to_display(value_internal: Any, unit_tag: str) -> Any:
    """
    Convert Revit internal storage into a UI/display value.
      - "mm": returns float mm (0 decimals typical for head/sill)
      - "cm": returns float centimetres
      - "m": returns float metres
      - "deg": returns float degrees
      - "bool": returns 0/1
      - default: string
    """
    ut = (unit_tag or "").lower()
    if ut == "mm":
        return ft_to_mm(float(value_internal))
    if ut == "cm":
        return ft_to_mm(float(value_internal)) / 10.0
    if ut == "m":
        return ft_to_mm(float(value_internal)) / 1000.0
    if ut == "deg":
        return rad_to_deg(float(value_internal))
    if ut == "bool":
        # Many integer containers store 0/1
        try:
            return 1 if bool(value_internal) else 0
        except Exception:
            return 0
    return "" if value_internal is None else str(value_internal)


# ---- Tolerant comparisons for lengths ----
def equal_mm(a_mm: float, b_mm: float, tol_mm: float = 0.5) -> bool:
    """Tolerant compare in millimetres (default ±0.5 mm)."""
    try:
        return abs(float(a_mm) - float(b_mm)) <= float(tol_mm)
    except Exception:
        return False


def equal_ft(a_ft: float, b_ft: float, tol_mm: float = 0.5) -> bool:
    """Tolerant compare in internal feet (compare by ±tol_mm)."""
    try:
        return equal_mm(ft_to_mm(a_ft), ft_to_mm(b_ft), tol_mm)
    except Exception:
        return False


# ---- Robust length parsing (UI text → mm) ----
def parse_length_mm(text: Any, default_mm: Optional[float] = None) -> Optional[float]:
    """
    Parse a user-entered length string into millimetres.
    Accepts forms like:
      "1200", "1200mm", "120 cm", "1.2m", "1,200 mm"
    (feet/inches not supported here—keep this millimetre-centric for ADa.)
    """
    if text is None:
        return default_mm
    s = str(text).strip().lower()
    if not s:
        return default_mm

    # Normalise separators
    s = s.replace(",", " ")
    toks = s.split()

    # Single token like "1200" or "1200mm"
    if len(toks) == 1:
        tk = toks[0]
        if tk.endswith("mm"):
            try:
                return float(tk[:-2])
            except Exception:
                return default_mm
        if tk.endswith("cm"):
            try:
                return float(tk[:-2]) * 10.0
            except Exception:
                return default_mm
        if tk.endswith("m") and not tk.endswith("mm"):
            try:
                return float(tk[:-1]) * 1000.0
            except Exception:
                return default_mm
        # plain number
        try:
            return float(tk)
        except Exception:
            return default_mm

    # Two tokens like "1200 mm", "1.2 m", "120 cm"
    if len(toks) >= 2:
        num, unit = toks[0], toks[1]
        try:
            v = float(num)
        except Exception:
            return default_mm
        if unit.startswith("mm"):
            return v
        if unit.startswith("cm"):
            return v * 10.0
        if unit in ("m", "meter", "metre", "meters", "metres"):
            return v * 1000.0

    return default_mm


# ---- Formatting helpers ----
def format_mm(value_ft: float, dp: int = 0, thousands: bool = False) -> str:
    """Format internal feet as mm with dp decimals (default 0).
    Set thousands=True to include thousands separators.
    """
    mm = ft_to_mm(value_ft)
    if thousands:
        # Use locale-independent thousands with commas
        fmt = "{:,." + str(int(dp)) + "f}"
    else:
        fmt = "{:." + str(int(dp)) + "f}"
    return fmt.format(mm)

def format_length(value_ft: float, style: str = "mm", dp: int = 0) -> str:
    """Format length in different metric styles for UI, using internal feet as input."""
    s = style.lower() if style else "mm"
    if s == "mm":
        return format_mm(value_ft, dp=dp)
    if s == "cm":
        return format_mm(value_ft, dp=max(0, dp))[:-3]  # rough: drop ' mm', keep number semantics
    if s == "m":
        m = ft_to_mm(value_ft) / 1000.0
        fmt = "{:." + str(int(dp)) + "f}"
        return fmt.format(m)
    return format_mm(value_ft, dp=dp)

# ---------------- Tiny GP helpers (kept & made sturdier) ----------------
# NOTE: In a future refactor these may move to ada_core.gp;
# we keep them here for backward compatibility and re-export from __all__.
def gp_spec_id_safe(kind: str, DB) -> Any:
    """Resolve common spec kinds to ForgeTypeId across API variants."""
    try:
        if kind == "Number":
            return DB.SpecTypeId.Number
        if kind == "YesNo":
            return DB.SpecTypeId.Boolean.YesNo
        if kind == "Length":
            return DB.SpecTypeId.Length
        if kind == "Angle":
            return DB.SpecTypeId.Angle
    except Exception:
        pass
    # Safe default
    try:
        return DB.SpecTypeId.String
    except Exception:
        return None


def create_or_find_gp_safe(doc, name: str, kind: str, default: Any = None, group=None) -> Tuple[Optional[Any], bool]:
    """
    Create or fetch a Global Parameter by name. Returns (ElementId, created_bool).
    kind: "Number" | "YesNo" | "Length" | "Angle"
    """
    from Autodesk.Revit import DB  # type: ignore
    try:
        gid = DB.GlobalParametersManager.FindByName(doc, name)
        if gid != DB.ElementId.InvalidElementId:
            return gid, False
    except Exception:
        pass
    try:
        ftid = gp_spec_id_safe(kind, DB)
        gp = DB.GlobalParameter.Create(doc, name, ftid if ftid is not None else DB.SpecTypeId.String)
        try:
            if group is not None:
                gp.GetDefinition().ParameterGroup = group
        except Exception:
            pass
        if default is not None:
            try:
                if kind == "YesNo":
                    v = DB.IntegerParameterValue(); v.Value = int(bool(default))
                elif kind == "Length":
                    v = DB.DoubleParameterValue(); v.Value = mm_to_ft(float(default))
                elif kind == "Angle":
                    v = DB.DoubleParameterValue(); v.Value = deg_to_rad(float(default))
                elif isinstance(default, (int, float)):
                    v = DB.DoubleParameterValue(); v.Value = float(default)
                else:
                    v = DB.StringParameterValue(); v.Value = str(default)
                gp.SetValue(v)
            except Exception:
                pass
        return gp.Id, True
    except Exception:
        return None, False


def create_legacy_gp_from_param_safe(doc, name: str, sample_param) -> Tuple[Optional[Any], bool]:
    """Create a GP using data type from an existing parameter. Returns (ElementId, created_bool)."""
    from Autodesk.Revit import DB  # type: ignore
    try:
        ftid = sample_param.Definition.GetDataType()
        # SpecUtils may not exist on older APIs—guard it
        try:
            ok = DB.SpecUtils.IsSpec(ftid)
        except Exception:
            ok = True  # assume OK on older APIs
        if not ok:
            return None, False
        gp = DB.GlobalParameter.Create(doc, name, ftid)
        return gp.Id, True
    except Exception:
        return None, False


def associate_params_safe(elements: Iterable, inst_to_gp_map: Dict[str, str], gp_ids: Dict[str, Any]) -> Tuple[int, list]:
    """Associate instance parameters to GPs. Returns (count, logs)."""
    from Autodesk.Revit import DB  # type: ignore
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
                logs.append("Failed {} on {}: {}".format(inst_name, getattr(el, "Id", "?"), e))
        if count:
            logs.append("Associated '{}' → '{}' on {} elements".format(inst_name, gp_name, count))
    return n, logs


__all__ = [
    # constants
    "MM_PER_FT", "FT_PER_MM",
    # core / legacy surface
    "mm_to_ft", "ft_to_mm", "parse_float", "is_zero_tol",
    "to_internal_length", "to_display_mm",
    # new general helpers
    "clamp", "safe_float", "round_mm", "floor_mm", "ceil_mm",
    "deg_to_rad", "rad_to_deg", "to_internal", "to_display",
    "equal_mm", "equal_ft", "parse_length_mm", "format_mm", "format_length",
    # safe GP utilities (kept)
    "gp_spec_id_safe", "create_or_find_gp_safe", "create_legacy_gp_from_param_safe", "associate_params_safe",
]
