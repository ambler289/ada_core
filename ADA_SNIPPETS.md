# ADa Core Snippets Catalog

_Auto-generated._

## __init__
*Tags: collect, selection, units, views | Deps: ada_core*

_No functions found_

## collect
*Tags: collect, params, selection, ui, views | Deps: revit_api, ada_core*

- **`_is_new_construction(elem)`**  
- **`windows_new_construction(doc, predicate)`**  
- **`windows_in_view(doc, view, predicate)`**  
- **`instances_of(doc, bic)`**  
  - Generic instance collector by BuiltInCategory.
- **`types_of(doc, bic)`**  
  - Generic type collector by BuiltInCategory.
- **`collect_by_scope_safe(doc, view, bic, scope_label, predicate)`** · **safe**  
  - Return (elements, scope_str) filtered by category and optional predicate.

## config
*Deps: ada_core*

- **`load_json(path, default)`**  
- **`save_json(path, data)`**  

## datums
*Tags: collect, params, views | Deps: revit_api*

- **`_scope_param(view)`**  
- **`_curve_in_view(lvl, view)`**  
- **`force_hide_level_bubbles(doc, view, pad_ft)`**  

## deps
*Deps: ada_core*

- **`ensure_paths(paths)`**  
- **`optional_import(name)`**  
- **`has(name)`**  

## doors
*Tags: params, units | Deps: revit_api*

- **`get_panel_width_mm(door_type)`**  
- **`set_panel_height_ft(door_type, height_ft)`**  

## elements
*Tags: params, units | Deps: revit_api*

- **`get_level_for_elem(doc, elem)`**  
- **`is_existing_phase(elem)`**  
- **`prefix_mark_dx(elem)`**  
  - Prefix string param 'Mark' with Dx (preserving common prefixes).

## errors
*Deps: ada_core*

- **`swallow(fn, *a, **kw)`**  
- **`retry(times, exceptions, fn, *a, **kw)`**  

## geom
*Tags: selection | Deps: revit_api, ada_core*

- **`bbox_from_elements(elements, expand)`**  
- **`line_overlap_1d(a0, a1, b0, b1, tol)`**  

## gp
*Tags: collect, gp, params, selection, units | Deps: revit_api, ada_core*

- **`_find_gp(doc, name)`**  
- **`ensure_gp(doc, name, ptype, group)`**  
  - Find a Global Parameter by name or create it. Returns (gp, created_bool).
- **`set_gp_value(doc, name, value, ptype, group)`**  
  - Create/ensure GP then set value using the correct value container.
- **`get_gp_value(doc, name, default)`**  
- **`map_global_parameters_by_name(doc)`**  
  - Create efficient name->GlobalParameter mapping for lookups.
- **`detect_global_parameter_associations(elements, doc)`**  
  - Detect GP associations using API handles and name matching.
- **`dissociate_global_parameter_safely(entry, doc)`**  
  - Safely dissociate GP while preserving parameter value.
- **`bulk_dissociate_global_parameters(associations, doc)`**  
  - Bulk dissociate GP associations; returns (removed, failed).
- **`gp_spec_id_safe(kind, DB)`** · **safe**  
  - Resolve common spec kinds to ForgeTypeId across API variants.
- **`create_or_find_gp_safe(doc, name, kind, default, group)`** · **safe**  
  - Create or fetch a Global Parameter by name. Returns (ElementId, created_bool).
- **`create_legacy_gp_from_param_safe(doc, name, sample_param)`** · **safe**  
  - Create a GP using data type from an existing parameter. Returns (ElementId, created_bool).
- **`associate_params_safe(elements, inst_to_gp_map, gp_ids)`** · **safe**  
  - Associate instance parameters to GPs. Returns (count, logs).

## graphics
*Tags: collect, views | Deps: revit_api, ada_core*

- **`get_line_pattern_id(doc, name)`**  
- **`ensure_line_subcategory(doc, parent_bic, subcat_name)`**  
- **`apply_line_style_override(view, subcat, line_pattern_id, weight)`**  
- **`delete_detail_curves_in_view(view, style_name)`**  

## ids
*Tags: selection | Deps: revit_api, ada_core*

- **`eid_int(eid)`**  
  - Robust ElementId → int.
- **`eid_str(eid)`**  
  - Human-readable ElementId string, safe for logs/UI.

## levels
*Tags: params | Deps: revit_api*

- **`is_ground_level(level)`**  
  - Matches 'ground', 'level 0', 'l0', 'grade' or ~0 elevation.

## log
*Deps: ada_core*

- **`log_info(*a)`**  
- **`log_warn(*a)`**  
- **`log_err(*a)`**  

## naming
*Deps: ada_core*

- **`slug(text, repl)`**  
- **`dedupe_name(base, existing_names, sep, max_len)`**  
- **`sequence(prefix, start, width)`**  

## params
*Tags: collect, params, selection, ui, units | Deps: revit_api, ada_core*

- **`specs_from_template(template_data)`**  
- **`get_element_id_value(element_id)`**  
- **`read_parameter_typed(param, DB)`**  
- **`write_parameter_typed(param, value_info)`**  
- **`get_parameter_element_id(param, DB)`**  
- **`get_parameter_by_name(element, param_name, DB)`**  
- **`has_parameter_value(param)`**  
- **`set_textnote_text_safe(tn, text, DB)`** · **safe**  
  - Set TextNote text via TEXT_TEXT; falls back to SetText if available. Returns bool.

## roofs
*Tags: selection | Deps: revit_api, ada_core*

- **`pick_roofs(uidoc, prompt)`**  
- **`roof_profile_curves(roof)`**  
  - Try to pull explicit footprint profiles (fast path).
- **`_slice_solid_edges_at_z(solid, z, tol)`**  
- **`slice_roof_at_z(roof, z, tol)`**  

## runtime
*Deps: pyrevit, ada_core*

- **`get_doc_uidoc()`**  
  - Return (uidoc, doc) from pyRevit runtime via __revit__ (unchanged).
- **`get_uiapp_app()`**  
  - Return (uiapp, app) using the same __revit__ handle.
- **`safe_get_doc_uidoc()`**  
  - Optional convenience: if __revit__ is missing for any reason,

## selection
*Tags: selection | Deps: revit_api, ada_core*

- **`preselected_of_types(uidoc, doc, *allowed_types)`**  
  - Return preselected elements filtered by the given types. Accepts *types or a single sequence.
- **`pick_until_esc(uidoc, doc, prompt, *allowed_types)`**  
  - Click elements of given types one-by-one until the user presses Esc. Returns list without duplicates.
- **`preselected_textnotes(uidoc, doc)`**  
  - Return preselected TextNotes if any, else [].
- **`pick_textnotes(uidoc, doc, prompt)`**  
  - Click TextNotes until Esc; filter on Python side to avoid ISelectionFilter quirks.
- **`safe_pick(uidoc, doc, prompt, allowed_types)`**  
  - Pick a single element; return None on Esc. Optionally restrict to types.
- **`pick_elements_by_category(uidoc, doc, prompt, categories, unique_only)`**  
  - Pick-until-Esc for specific BuiltInCategories; returns elements (unique if unique_only).

## tags
*Tags: selection, views | Deps: revit_api*

- **`tag_element(doc, view, elem, symbol)`**  

## text
*Deps: ada_core*

- **`convert_case(txt, mode)`**  
  - Convert text according to mode: 'lowercase', 'UPPERCASE', 'Title Case'.

## transactions
*Tags: units | Deps: revit_api*

- **`batched(doc, name, items, fn)`**  

## tx
*Tags: units | Deps: revit_api, ada_core*

- **`transact(doc, name)`**  
  - Usage:
- **`run_in_tx(doc, name, fn)`**  
  - Run a callable inside a transaction and return its result.
- **`subtransact(doc, name)`**  
  - Semantically separate nested scopes; same as transact.

## txn
*Tags: units | Deps: revit_api, ada_core*

- **`in_txn(doc, name)`**  
  - Decorator: run function in a transaction.

## types
*Tags: collect, params | Deps: revit_api*

- **`find_type_by_name_and_family(doc, type_name, family_name)`**  
- **`duplicate_type_with_name(orig_type, new_name)`**  

## ui
*Tags: ui, units | Deps: revit_api, pyrevit, ada_bootstrap, ada_brandforms_v6*

- **`_forms()`**  
- **`alert(message, title)`**  
- **`confirm(message, title)`**  
- **`choose_yes_no(message, title, yes, no)`**  
- **`ask_string(prompt, default, title)`**  
- **`_ada_v6_buttons(title, message, buttons)`**  
- **`alert_v6(msg, title)`**  
  - Themed alert preferred (v6-first).
- **`confirm_v6(msg, title)`**  
  - Themed Yes/No; returns bool. Never overrides existing confirm().
- **`big_buttons(title, options, message, cancel)`**  
  - Three-button style chooser.

## ui_bulk
*Tags: params, ui, units | Deps: revit_api*

- **`_ada_safe_text(val)`**  
- **`_ada_style_button(btn, primary)`**  
- **`edit_parameters_bulk_winforms(template_data, sample_window, title)`**  

## units
*Tags: gp, params, selection, units | Deps: revit_api, ada_core*

- **`mm_to_ft(mm)`**  
- **`ft_to_mm(ft)`**  
- **`parse_float(text, default)`**  
- **`is_zero_tol(a, b, tol)`**  
- **`to_internal_length(value_mm)`**  
  - Convenience alias for mm_to_ft with clearer intent.
- **`to_display_mm(value_ft)`**  
  - Alias for ft_to_mm; name mirrors intent in UI code.
- **`gp_spec_id_safe(kind, DB)`** · **safe**  
  - Resolve common spec kinds to ForgeTypeId across API variants.
- **`create_or_find_gp_safe(doc, name, kind, default, group)`** · **safe**  
  - Create or fetch a Global Parameter by name. Returns (ElementId, created_bool).
- **`create_legacy_gp_from_param_safe(doc, name, sample_param)`** · **safe**  
  - Create a GP using data type from an existing parameter. Returns (ElementId, created_bool).
- **`associate_params_safe(elements, inst_to_gp_map, gp_ids)`** · **safe**  
  - Associate instance parameters to GPs. Returns (count, logs).

## views
*Tags: collect, params, ui, views | Deps: revit_api*

- **`section_type(doc, name)`**  
- **`view_template_id(doc, name)`**  
- **`tag_symbol(doc, family_name)`**  
- **`windows(doc, only_new, exclude_skylights)`**  
- **`taken_view_names(doc)`**  
- **`unique_name(base, taken)`**  
- **`create_window_section(doc, window, vft, taken, offset_ft=?, interior_ft=?, exterior_margin_ft=?, base_offset_ft=?, extra_headroom_ft=?, head_ft=?)`**  
- **`ensure_section_type(doc, name, fallback_first)`**  
  - Return section ViewFamilyType by name, or first available if fallback_first=True.

## viewsheets
*Tags: views | Deps: revit_api, ada_core*

- **`place_view_on_sheet(doc, sheet, view, pt)`**  
- **`grid_layout(count, cols, cell_w, cell_h, start, gutter_w, gutter_h)`**  
  - Return a list of XYZ positions for a grid with 'count' items.
