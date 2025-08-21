# ADa UI Capability Matrix

_Detected theming providers in your extension (highest priority first)._

| Provider | Version | Alert buttons | Provides | Path |
|---|---:|:---:|---|---|
| ada_brandforms_v6 | 6 | ✔ | alert, ask_yes_no, big_button_box, input_box, select_from_list | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_brandforms_v6.py |
| ada_brandforms_v5 | 5 | ✔ | alert, ask_yes_no | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_brandforms_v5.py |
| ada_brandforms_v4_2 | 4_2 | — | — | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_brandforms_v4_2.py |
| ada_brandforms_v4 | 4 | — | — | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_brandforms_v4.py |
| ada_brandforms_v3 | 3 | — | — | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_brandforms_v3.py |
| ada_bootstrap |  | — | — | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\ada_bootstrap.py |
| gp_ui_shims |  | — | — | C:\Users\jon\AppData\Roaming\pyRevit\Extensions\ADa-Manage.extension\lib\gp_ui_shims.py |

## Recommended dynamic import order
```python
def themed_alert(msg, title='Message', buttons=None):
    mods = ['ada_brandforms_v6', 'ada_brandforms_v5', 'ada_brandforms_v4_2', 'ada_brandforms_v4', 'ada_brandforms_v3', 'ada_bootstrap', 'gp_ui_shims']
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