# ADa UI Capability Matrix

_Detected theming providers in your extension (highest priority first)._

| Provider | Version | Alert buttons | Provides | Path |
|---|---:|:---:|---|---|

## Recommended dynamic import order
```python
def themed_alert(msg, title='Message', buttons=None):
    mods = []
    for mn in mods:
        try:
            m = __import__(mn, fromlist=['alert'])
            fn = getattr(m, 'alert', None)
            if fn:
                if buttons is None:
                    return fn(str(msg), title=str(title))
                try:  return fn(str(msg), title=str(title), buttons=list(buttons))
                except TypeError:
                    if buttons and set(buttons)==set(['Yes','No']) and hasattr(m,'confirm'):
                        return 'Yes' if m.confirm(str(msg), title=str(title)) else 'No'
                return fn(str(msg), title=str(title))
        except Exception:  continue
    try:
        from pyrevit import forms
        if buttons and set(buttons)==set(['Yes','No']):
            return 'Yes' if forms.alert(str(msg), title=str(title), yes=True, no=True) else 'No'
        return forms.alert(str(msg), title=str(title))
    except Exception:
        print('[ALERT]', title, msg); return None
```