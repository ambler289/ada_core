# ada_core/txn.py
from Autodesk.Revit.DB import Transaction

class Tx(object):
    def __init__(self, doc, name):
        self.doc, self.name = doc, name
        self.t = None
    def __enter__(self):
        self.t = Transaction(self.doc, self.name); self.t.Start(); return self
    def __exit__(self, et, ev, tb):
        if et: self.t.RollBack()
        else:  self.t.Commit()
        return False  # propagate exceptions

def in_txn(doc, name):
    """Decorator: run function in a transaction."""
    def deco(fn):
        def wrap(*args, **kwargs):
            with Tx(doc, name):
                return fn(*args, **kwargs)
        return wrap
    return deco
