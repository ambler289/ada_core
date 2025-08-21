# ada_core/naming.py — generic naming helpers
import re, itertools

def slug(text, repl="_"):
    s = re.sub(r"[^A-Za-z0-9]+", repl, text or "")
    return s.strip(repl)

def dedupe_name(base, existing_names, sep="-", max_len=64):
    base = (base or "Item")[:max_len]
    low = base.lower()
    if low not in existing_names:
        existing_names.add(low)
        return base
    for i in itertools.count(2):
        name = f"{base}{sep}{i}"
        if name.lower() not in existing_names:
            existing_names.add(name.lower())
            return name

def sequence(prefix, start=1, width=2):
    n = int(start)
    while True:
        yield f"{prefix}{str(n).zfill(width)}"
        n += 1
