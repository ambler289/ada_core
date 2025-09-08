
# -*- coding: utf-8 -*-
"""ada_core.gp (2026-safe)
Global Parameter helpers compatible with Revit 2024–2026+ (CPython3).
- Avoids import-time references to DB.ParameterType
- Uses SpecTypeId when available (2021+), falls back gracefully
- No default args that touch deprecated enums
"""
from __future__ import annotations

from typing import Any, Tuple, Optional
from Autodesk.Revit import DB  # type: ignore

# ------------------------------------------------------------
# Version/feature detection
# ------------------------------------------------------------
_HAS_SPEC = hasattr(DB, "SpecTypeId")
_BOOL_PATH = ("Boolean", "YesNo")  # SpecTypeId.Boolean.YesNo

# ------------------------------------------------------------
# Spec helpers (lazy; safe on all versions)
# ------------------------------------------------------------
def _spec_text():
    if _HAS_SPEC:
        return DB.SpecTypeId.String
    return getattr(DB, "ParameterType").Text  # pragma: no cover

def _spec_yesno():
    if _HAS_SPEC:
        return getattr(DB.SpecTypeId, _BOOL_PATH[0]).YesNo
    return getattr(DB, "ParameterType").YesNo  # pragma: no cover

def _spec_length():
    if _HAS_SPEC:
        return DB.SpecTypeId.Length
    return getattr(DB, "ParameterType").Length  # pragma: no cover

def _spec_angle():
    if _HAS_SPEC:
        return DB.SpecTypeId.Angle
    return getattr(DB, "ParameterType").Angle  # pragma: no cover

def _spec_number():
    if _HAS_SPEC:
        return DB.SpecTypeId.Number
    return getattr(DB, "ParameterType").Number  # pragma: no cover

# ------------------------------------------------------------
# Coercion utilities
# ------------------------------------------------------------
def _coerce_spec(ptype: Any):
    """Return a DB.ForgeTypeId for the desired data type.
    Accepts: ForgeTypeId (pass-through), ParameterType enums (legacy),
    strings like 'text','yesno','length','angle','number'.
    """
    # Already a ForgeTypeId (SpecTypeId or DataTypeId)
    if isinstance(ptype, DB.ForgeTypeId):
        return ptype

    # Strings (case-insensitive)
    if isinstance(ptype, str):
        key = ptype.strip().lower()
        if key in ("text", "string", "str"):
            return _spec_text()
        if key in ("yesno", "bool", "boolean"):
            return _spec_yesno()
        if key in ("len", "length", "mm", "m", "ft", "feet", "meter", "metre"):
            return _spec_length()
        if key in ("ang", "angle", "deg", "degree", "degrees"):
            return _spec_angle()
        if key in ("num", "number", "double", "float", "real"):
            return _spec_number()

    # Legacy ParameterType enums (only exist pre-2026)
    PT = getattr(DB, "ParameterType", None)
    if PT is not None:
        try:
            # name like "Text", "YesNo", etc.
            enum_name = str(ptype)
            if enum_name.startswith("ParameterType."):
                enum_name = enum_name.split(".", 1)[-1]
            enum_name = enum_name.lower()
            mapping = {
                "text": _spec_text,
                "yesno": _spec_yesno,
                "length": _spec_length,
                "angle": _spec_angle,
                "number": _spec_number,
                "integer": _spec_number,
            }
            if enum_name in mapping:
                return mapping[enum_name]()
        except Exception:
            pass

    # Fallback to text spec
    return _spec_text()

# ------------------------------------------------------------
# ParameterValue construction
# ------------------------------------------------------------
def _make_value(spec: DB.ForgeTypeId, value: Any) -> DB.ParameterValue:
    """Create the appropriate DB.ParameterValue for a given spec + python value."""
    # Boolean
    try:
        bool_id = getattr(DB.SpecTypeId, _BOOL_PATH[0]).YesNo if _HAS_SPEC else None
    except Exception:
        bool_id = None

    if _HAS_SPEC:
        if spec == DB.SpecTypeId.String:
            return DB.StringParameterValue(str(value) if value is not None else "")
        if bool_id is not None and spec == bool_id:
            return DB.IntegerParameterValue(1 if bool(value) else 0)
        # numeric-like specs → Double
        if spec in (DB.SpecTypeId.Length, DB.SpecTypeId.Angle, DB.SpecTypeId.Number):
            try:
                return DB.DoubleParameterValue(float(value))
            except Exception:
                return DB.DoubleParameterValue(0.0)
        # default to string
        return DB.StringParameterValue(str(value) if value is not None else "")
    else:
        # Legacy path (unlikely on 2026, here for completeness)
        PT = DB.ParameterType
        if spec == PT.Text:
            return DB.StringParameterValue(str(value) if value is not None else "")
        if spec == PT.YesNo:
            return DB.IntegerParameterValue(1 if bool(value) else 0)
        # double-ish
        try:
            return DB.DoubleParameterValue(float(value))
        except Exception:
            return DB.DoubleParameterValue(0.0)

# ------------------------------------------------------------
# Core find/create helpers
# ------------------------------------------------------------
def _find_gp(doc: DB.Document, name: str) -> Optional[DB.GlobalParameter]:
    it = DB.FilteredElementCollector(doc).OfClass(DB.GlobalParameter)
    for gp in it:  # type: ignore
        if gp.Name == name:
            return gp  # type: ignore[return-value]
    return None

def ensure_gp(doc: DB.Document, name: str, ptype: Any = None,
              group: DB.BuiltInParameterGroup = DB.BuiltInParameterGroup.PG_DATA
              ) -> Tuple[DB.GlobalParameter, bool]:
    """Get or create a Global Parameter.
    Returns (gp, created).
    NOTE: Caller is responsible for wrapping in a Transaction.
    """
    gp = _find_gp(doc, name)
    if gp:
        # Ensure correct group if mismatch
        try:
            if gp.GetGroup() != group:
                gp.SetGroup(group)
        except Exception:
            pass
        return gp, False

    spec = _coerce_spec(ptype if ptype is not None else _spec_text())
    gp = DB.GlobalParameter.Create(doc, name, spec)
    try:
        gp.SetGroup(group)
    except Exception:
        pass
    return gp, True

def set_gp_value(doc: DB.Document, name: str, value: Any, ptype: Any = None,
                 group: DB.BuiltInParameterGroup = DB.BuiltInParameterGroup.PG_DATA
                 ) -> DB.GlobalParameter:
    """Create (if needed) and set a Global Parameter value."""
    spec = _coerce_spec(ptype if ptype is not None else _spec_text())
    gp, _ = ensure_gp(doc, name, spec, group)
    pv = _make_value(spec, value)
    gp.SetValue(pv)
    return gp

# ------------------------------------------------------------
# Convenience setter with unit tags (text/yesno/length/angle)
# ------------------------------------------------------------
def set_gp_value_unit(doc: DB.Document, name: str, unit_tag: str, value: Any
                      ) -> DB.GlobalParameter:
    tag = (unit_tag or "").strip().lower()
    if tag in ("bool", "yesno", "boolean"):
        return set_gp_value(doc, name, bool(value), _spec_yesno())
    if tag in ("mm", "millimeter", "millimetre"):
        # Convert mm → ft if units helper is present
        try:
            from ada_core.units import mm_to_ft  # type: ignore
            val = float(mm_to_ft(float(value)))
        except Exception:
            val = float(value)
        return set_gp_value(doc, name, val, _spec_length())
    if tag in ("deg", "degree", "degrees"):
        try:
            from ada_core.units import deg_to_rad  # type: ignore
            val = float(deg_to_rad(float(value)))
        except Exception:
            val = float(value)
        return set_gp_value(doc, name, val, _spec_angle())
    if tag in ("num", "number"):
        return set_gp_value(doc, name, float(value), _spec_number())

    # default to text
    return set_gp_value(doc, name, "" if value is None else str(value), _spec_text())
