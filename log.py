# ada_core/log.py — simple diagnostics
import time, sys

def log_info(*a): print("[INFO]", *a)
def log_warn(*a): print("[WARN]", *a, file=sys.stderr)
def log_err(*a):  print("[ERR ]", *a, file=sys.stderr)

class time_block:
    def __init__(self, label): self.label = label; self.t0 = None
    def __enter__(self): self.t0 = time.time(); return self
    def __exit__(self, et, e, tb):
        dt = time.time() - self.t0 if self.t0 else 0.0
        print("[TIME]", self.label, "{:.3f}s".format(dt))
