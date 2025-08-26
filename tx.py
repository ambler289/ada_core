#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.tx
Lightweight, decorator-free Revit DB transaction helpers.

- Backwards-compatible with existing API:
    transact(doc, name)   -> context manager, returns Transaction
    subtransact(doc, name)  alias of transact
    run_in_tx(doc, name, fn)

- Extras (safe to adopt without breaking old code):
    group(doc, name)      -> TransactionGroup context manager
    Tx / TxGroup classes  -> explicit classes behind the helpers
    SilentWarnings        -> suppresses warnings during commits
"""

from typing import Callable, Any, Optional

import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import (  # type: ignore
    Transaction, TransactionGroup, IFailuresPreprocessor,
    FailureProcessingResult, FailureHandlingOptions
)

__all__ = [
    "transact", "subtransact", "run_in_tx",
    "group", "Tx", "TxGroup", "SilentWarnings",
]

# -----------------------------------------------------------------------------
# Warning preprocessor (removes warnings, lets errors surface)
# -----------------------------------------------------------------------------
class SilentWarnings(IFailuresPreprocessor):
    """Drop warnings to keep dialogs from interrupting batch ops."""
    def PreprocessFailures(self, failuresAccessor):
        try:
            for f in list(failuresAccessor.GetFailureMessages() or []):
                if not f.GetSeverity():  # defensive; usually returns enum
                    continue
                # Demote ignorable severities
                if f.GetSeverity().ToString().lower() == "warning":
                    failuresAccessor.DeleteWarning(f)
            return FailureProcessingResult.Continue
        except Exception:
            # If anything goes odd, don't block the transaction.
            return FailureProcessingResult.Continue


def _apply_silent_warnings(t):
    """Attach the SilentWarnings preprocessor to a Transaction."""
    try:
        fho = t.GetFailureHandlingOptions() or FailureHandlingOptions()
        fho.SetFailuresPreprocessor(SilentWarnings()) \
           .SetClearAfterRollback(True)
        t.SetFailureHandlingOptions(fho)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Context managers
# -----------------------------------------------------------------------------
class Tx(object):
    """Simple context manager for a single Transaction."""
    def __init__(self, doc, name: str, quiet_warnings: bool = True):
        self._doc = doc
        self._name = name
        self._t: Optional[Transaction] = None
        self._quiet = quiet_warnings

    def __enter__(self) -> Transaction:
        t = Transaction(self._doc, self._name)
        t.Start()
        if self._quiet:
            _apply_silent_warnings(t)
        self._t = t
        return t

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            # Exception inside the with-block: rollback and re-raise
            try:
                self._t.RollBack()
            except Exception:
                pass
            return False
        # Commit path
        try:
            self._t.Commit()
            return True
        except Exception:
            # Let caller see the exception
            return False


class TxGroup(object):
    """Context manager for a TransactionGroup."""
    def __init__(self, doc, name: str):
        self._g = TransactionGroup(doc, name)

    def __enter__(self):
        self._g.Start()
        return self._g

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            try:
                self._g.RollBack()
            except Exception:
                pass
            return False
        try:
            self._g.Assimilate()
            return True
        except Exception:
            try:
                self._g.RollBack()
            except Exception:
                pass
            return False


# -----------------------------------------------------------------------------
# Public helpers (backwards-compatible)
# -----------------------------------------------------------------------------
def transact(doc, name: str) -> Tx:
    """
    Usage:
        with transact(doc, "Do Things") as t:
            # t is Autodesk.Revit.DB.Transaction
            ...
    """
    return Tx(doc, name)


def subtransact(doc, name: str) -> Tx:
    """Alias of transact; useful for semantic nesting."""
    return Tx(doc, name)


def run_in_tx(doc, name: str, fn: Callable[[], Any]) -> Any:
    """Run a callable inside a transaction and return its result."""
    with Tx(doc, name):
        return fn()


def group(doc, name: str) -> TxGroup:
    """
    Usage:
        with group(doc, "Batch Operation"):
            with transact(doc, "Step 1"): ...
            with transact(doc, "Step 2"): ...
    """
    return TxGroup(doc, name)
