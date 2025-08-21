# ada_core/deps.py — environment helpers
import sys, importlib

def ensure_paths(paths):
    for p in paths or []:
        if p and p not in sys.path:
            sys.path.insert(0, p)

def optional_import(name):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

def has(name):
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False
