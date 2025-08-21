#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.tx
Transaction helpers for Revit DB work (decorator-free to avoid contextlib shadowing).
"""

import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import Transaction  # type: ignore
from typing import Callable, Any

class _TxCtx(object):
    """Simple class-based context manager for Revit transactions."""
    def __init__(self, doc, name: str):
        self._doc = doc
        self._name = name
        self._t = None

    def __enter__(self):
        self._t = Transaction(self._doc, self._name)
        self._t.Start()
        return self._t  # keep behavior compatible with previous 'yield t'

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            try:
                self._t.RollBack()
            except Exception:
                pass
            # re-raise exception
            return False
        try:
            self._t.Commit()
        except Exception:
            # let exceptions propagate
            return False
        return True

def transact(doc, name: str):
    """
    Usage:
        with transact(doc, "Do Things") as t:
            ...
    """
    return _TxCtx(doc, name)

def run_in_tx(doc, name: str, fn: Callable[[], Any]) -> Any:
    """Run a callable inside a transaction and return its result."""
    with transact(doc, name):
        return fn()

def subtransact(doc, name: str):
    """Semantically separate nested scopes; same as transact."""
    return transact(doc, name)
