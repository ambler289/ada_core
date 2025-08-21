# ada_core/errors.py — small error utilities
def swallow(fn, *a, **kw):
    try:
        return True, fn(*a, **kw)
    except Exception as e:
        return False, e

def retry(times, exceptions, fn, *a, **kw):
    last = None
    for _ in range(int(times)):
        try:
            return fn(*a, **kw)
        except exceptions as e:
            last = e
    if last:
        raise last
