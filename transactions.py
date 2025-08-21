# ada_code/transactions.py — lean, shared transaction helpers
from Autodesk.Revit import DB

class tx(object):
    def __init__(self, doc, name):
        self.doc, self.name, self.t = doc, name, None
    def __enter__(self):
        self.t = DB.Transaction(self.doc, self.name)
        self.t.Start()
        return self
    def __exit__(self, et, e, tb):
        if et:
            self.t.RollBack()
        else:
            self.t.Commit()

class group(object):
    def __init__(self, doc, name):
        self.g = DB.TransactionGroup(doc, name)
    def __enter__(self):
        self.g.Start()
        return self
    def __exit__(self, et, e, tb):
        if et:
            self.g.RollBack()
        else:
            try:
                self.g.Assimilate()
            except Exception:
                self.g.RollBack()

def batched(doc, name, items, fn):
    done = fail = 0
    with group(doc, name):
        for it in items or []:
            try:
                label = getattr(it, "Id", it)
                with tx(doc, "{}: {}".format(name, label)):
                    fn(it)
                done += 1
            except Exception:
                fail += 1
    return done, fail
