# ada_core/templates.py — template & project-config loader/saver + naming
# Safe, filesystem-only. No Revit dependency.

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, List
import os, json, datetime

__all__ = [
    "TemplateManager", "resolve_roots",
    "legacy_timestamp", "build_prefix_from_template",
]

# Defaults (match your current structure)
DEFAULT_CONFIG_ROOT = r"C:\ADa\ADarchitecture Limited\ADA - Documents\Tech_Library\Revit\ADa_Library\ADa JSON Config"
DEFAULT_TEMPLATES_SUBFOLDER = "Wall_Type_Templates"
DEFAULT_PROJECTS_SUBFOLDER  = "Project_Configurations"

# Environment overrides (opt-in, won’t break anything if unset)
ENV_ROOT   = "ADA_JSON_CONFIG_DIR"      # overrides the root entirely
ENV_TEMPL  = "ADA_TEMPLATES_DIR"        # overrides only templates dir
ENV_PROJ   = "ADA_PROJECT_CONFIG_DIR"   # overrides only project configs dir

def resolve_roots() -> Tuple[str, str]:
    """
    Returns (templates_dir, projects_dir), considering env overrides.
    Both paths are guaranteed to exist (created if missing).
    """
    root = os.getenv(ENV_ROOT, DEFAULT_CONFIG_ROOT)
    templ = os.getenv(ENV_TEMPL, os.path.join(root, DEFAULT_TEMPLATES_SUBFOLDER))
    proj  = os.getenv(ENV_PROJ,  os.path.join(root, DEFAULT_PROJECTS_SUBFOLDER))
    for p in (templ, proj):
        try:
            if p and not os.path.isdir(p):
                os.makedirs(p)
        except Exception:
            pass
    return templ, proj

def legacy_timestamp() -> str:
    """MMDD_HHMM — matches your legacy unique suffix style."""
    return datetime.datetime.now().strftime("%m%d_%H%M")

def build_prefix_from_template(tpl: Dict[str, Any]) -> str:
    """
    Produce a short, unique prefix from template data:
      <nameNoSpaces[0:12]>_<MMDD_HHMM>
    """
    wt = (tpl.get("wall_type_configuration") or {}) if isinstance(tpl, dict) else {}
    nm = (wt.get("name") or "Custom")
    nm = "".join(c for c in nm if c.isalnum())[:12] or "Custom"
    return "{}_{}".format(nm, legacy_timestamp())

class TemplateManager(object):
    """
    Lightweight manager to list+load templates and save “project configurations”.
    - Reads *.json from the templates folder.
    - Performs light validation (no hard schema).
    - Can prompt a selection via the passed UI facade (optional).
    """

    def __init__(self, templates_dir: Optional[str] = None, projects_dir: Optional[str] = None):
        td, pd = resolve_roots()
        self.templates_dir = templates_dir or td
        self.projects_dir  = projects_dir  or pd

    # -------- Discovery --------
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns:
          {
            display_name: {
              "filepath": "...",
              "data": {...},               # parsed json
              "description": "..."
            },
            ...
          }
        """
        results: Dict[str, Dict[str, Any]] = {}
        if not os.path.isdir(self.templates_dir):
            return results
        for fn in sorted(os.listdir(self.templates_dir)):
            if not fn.lower().endswith(".json"):
                continue
            fp = os.path.join(self.templates_dir, fn)
            try:
                with open(fp, "r") as f:
                    data = json.load(f)
                info = (data.get("template_info") or {}) if isinstance(data, dict) else {}
                disp = info.get("name") or os.path.splitext(fn)[0].replace("_", " ")
                desc = info.get("description", "No description available")
                results[disp] = {"filepath": fp, "data": data, "description": desc}
            except Exception:
                # skip unreadable/malformed files silently
                continue
        return results

    # -------- Selection (optional UI) --------
    def select_template_ui(self, ui=None, title: str = "Select Template") -> Optional[Dict[str, Any]]:
        """
        Open a simple chooser (if a ui facade with big_buttons exists).
        Returns { 'filepath':..., 'data':..., 'description':... } or None.
        """
        tpl_map = self.list_templates()
        if not tpl_map:
            if ui: ui.alert("No templates found in:\n{}".format(self.templates_dir), title="No Templates")
            return None
        items, lookup = [], {}
        for disp, info in tpl_map.items():
            label = "{}\n  {}".format(disp, info.get("description", ""))
            items.append(label); lookup[label] = info
        chosen = None
        if ui and hasattr(ui, "big_buttons"):
            chosen = ui.big_buttons(title=title, options=items, message="")
        else:
            # console fallback
            print("\n" + title)
            for i, o in enumerate(items, 1): print("{:>2}. {}".format(i, o))
            raw = input("Choose [1-{}]: ".format(len(items))).strip()
            try:
                k = int(raw); chosen = items[k-1]
            except Exception:
                chosen = None
        return lookup.get(chosen)

    # -------- Save / load --------
    def save_project_config(self, payload: Dict[str, Any], name_hint: str = "project") -> Optional[str]:
        """
        Saves payload as JSON into the projects directory.
        Filename: <name_hint>__<timestamp>.json
        Returns full path or None on failure.
        """
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if (c.isalnum() or c in "_- ") else "_" for c in (name_hint or "project")).strip() or "project"
        fname = "{}__{}.json".format(safe, ts)
        fpath = os.path.join(self.projects_dir, fname)
        try:
            with open(fpath, "w") as f:
                json.dump(payload, f, indent=2)
            return fpath
        except Exception:
            return None

    def load_json(self, filepath: str) -> Optional[Dict[str, Any]]:
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return None
