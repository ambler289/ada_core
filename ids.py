#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.ids
Helpers for element/document ID handling.
"""

from typing import Any

def eid_int(eid: Any) -> int:
    """
    Robust ElementId → int.
    Keeps existing behavior:
      1) try eid.IntegerValue
      2) try eid.Value
      3) try int(str(eid))
      4) else -1
    """
    try:
        return int(eid.IntegerValue)   # IronPython & many pythonnet builds
    except Exception:
        v = getattr(eid, "Value", None)
        if v is not None:
            try:
                return int(v)
            except Exception:
                pass
    try:
        return int(str(eid))
    except Exception:
        return -1

def eid_str(eid: Any) -> str:
    """Human-readable ElementId string, safe for logs/UI."""
    try:
        iv = getattr(eid, "IntegerValue", None)
        if iv is not None:
            return str(int(iv))
    except Exception:
        pass
    try:
        return str(int(eid))
    except Exception:
        return str(eid)
