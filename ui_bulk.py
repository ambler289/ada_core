import clr
clr.AddReference("System")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import (
    Form, TableLayoutPanel, Label, TextBox, CheckBox, Button, FlowLayoutPanel,
    FormBorderStyle, DockStyle, Padding, DialogResult, CheckState,
    FormStartPosition, FlatStyle, BorderStyle, FlowDirection
)
from System.Drawing import Size, Font, FontStyle, ContentAlignment, Color
from System.Drawing.Drawing2D import LinearGradientBrush, LinearGradientMode

def _ada_safe_text(val):
    if val is None:
        return ""
    try:
        if isinstance(val, float):
            return ("{:.0f}".format(val) if val.is_integer() else "{:g}".format(val))
        return str(val)
    except Exception:
        return ""

def _ada_style_button(btn, primary=False):
    btn.FlatStyle = FlatStyle.Flat
    btn.FlatAppearance.BorderSize = 0  # int OK
    btn.BackColor = Color.FromArgb(92, 124, 250) if primary else Color.FromArgb(247, 89, 192)
    btn.ForeColor = Color.White
    btn.Height = 34
    btn.Width = 120

def edit_parameters_bulk_winforms(self, template_data, sample_window, title="Edit Parameters (Bulk)"):
    editable_params = self.get_editable_parameters(template_data, sample_window)
    if not editable_params:
        return None

    BG = Color.FromArgb(20, 22, 26)           # main background
    TEXT = Color.White
    FIELD_BG = Color.FromArgb(36, 39, 46)

    # Form
    form = Form()
    form.Text = title
    form.StartPosition = FormStartPosition.CenterScreen                 # enum-safe
    form.FormBorderStyle = FormBorderStyle.FixedDialog                  # enum-safe
    form.MinimizeBox = False
    form.MaximizeBox = False
    form.BackColor = BG
    form.ForeColor = TEXT
    form.Font = Font("Segoe UI", 9.0)
    form.Size = Size(860, 560)

    # Header gradient
    header = Label()
    header.Dock = DockStyle.Top
    header.Height = 64
    header.Text = "  " + title
    header.Font = Font("Segoe UI Semibold", 12.0, FontStyle.Bold)       # enum-safe
    header.ForeColor = Color.White
    def _paint_header(sender, e):
        rect = sender.ClientRectangle
        brush = LinearGradientBrush(rect, Color.FromArgb(92,124,250), Color.FromArgb(247,89,192), LinearGradientMode.Horizontal)
        e.Graphics.FillRectangle(brush, rect)
        brush.Dispose()
    header.Paint += _paint_header
    header.TextAlign = ContentAlignment.MiddleLeft                      # enum-safe
    form.Controls.Add(header)

    # Content grid
    content = TableLayoutPanel()
    content.Dock = DockStyle.Fill
    content.Padding = Padding(16, 16, 16, 8)
    content.BackColor = BG
    content.ColumnCount = 4
    content.RowCount = 1
    content.AutoScroll = True

    hdr_font = Font("Segoe UI", 9.0, FontStyle.Bold)
    def _hdr(text):
        lbl = Label()
        lbl.Text = text
        lbl.Font = hdr_font
        lbl.AutoSize = True
        lbl.ForeColor = TEXT
        lbl.BackColor = BG
        lbl.TextAlign = ContentAlignment.MiddleLeft
        return lbl

    content.Controls.Add(_hdr("Parameter"), 0, 0)
    content.Controls.Add(_hdr("Current"),   1, 0)
    content.Controls.Add(_hdr("New Value"), 2, 0)
    content.Controls.Add(_hdr("Unit"),      3, 0)

    editors = []
    row = 1
    for p in editable_params:
        name        = p['name']
        display     = p['display_name']
        ptype       = p['type']
        current     = p['value']
        unit        = p.get('config', {}).get('unit', '') or ''

        name_lbl = Label()
        name_lbl.Text = _ada_safe_text(display)
        name_lbl.AutoSize = True
        name_lbl.ForeColor = TEXT
        name_lbl.BackColor = BG
        name_lbl.TextAlign = ContentAlignment.MiddleLeft

        curr_lbl = Label()
        curr_lbl.Text = _ada_safe_text(current if ptype != 'bool' else ("Yes" if current else "No"))
        curr_lbl.AutoSize = True
        curr_lbl.ForeColor = TEXT
        curr_lbl.BackColor = BG
        curr_lbl.TextAlign = ContentAlignment.MiddleLeft

        content.Controls.Add(name_lbl, 0, row)
        content.Controls.Add(curr_lbl, 1, row)

        if ptype == 'bool':
            cb = CheckBox()
            cb.ThreeState = True
            cb.CheckState = CheckState.Indeterminate                      # enum-safe
            cb.Text = " (tick = Yes, untick = No; dash = keep)"
            cb.AutoSize = True
            cb.ForeColor = TEXT
            cb.BackColor = BG
            content.Controls.Add(cb, 2, row)
            content.Controls.Add(Label(), 3, row)                          # empty unit cell
            editors.append(("bool", name, cb, ptype, unit))
        else:
            tb = TextBox()
            tb.Width = 260
            tb.Text = _ada_safe_text(current)
            tb.BackColor = FIELD_BG
            tb.ForeColor = TEXT
            tb.BorderStyle = BorderStyle.FixedSingle                       # enum-safe (was int 1)
            content.Controls.Add(tb, 2, row)

            unit_lbl = Label()
            unit_lbl.Text = _ada_safe_text(unit)
            unit_lbl.AutoSize = True
            unit_lbl.ForeColor = TEXT
            unit_lbl.BackColor = BG
            content.Controls.Add(unit_lbl, 3, row)
            editors.append(("text", name, tb, ptype, unit))

        row += 1

    # Buttons
    btn_panel = FlowLayoutPanel()
    btn_panel.Dock = DockStyle.Bottom
    btn_panel.FlowDirection = FlowDirection.RightToLeft                  # enum-safe (was int 2)
    btn_panel.Padding = Padding(16, 8, 16, 16)
    btn_panel.BackColor = BG

    btn_ok = Button()
    btn_ok.Text = "OK"
    btn_ok.DialogResult = DialogResult.OK                                # enum-safe
    _ada_style_button(btn_ok, primary=True)

    btn_cancel = Button()
    btn_cancel.Text = "Cancel"
    btn_cancel.DialogResult = DialogResult.Cancel                        # enum-safe
    _ada_style_button(btn_cancel, primary=False)

    btn_panel.Controls.Add(btn_cancel)
    btn_panel.Controls.Add(btn_ok)

    form.AcceptButton = btn_ok
    form.CancelButton = btn_cancel
    form.Controls.Add(btn_panel)
    form.Controls.Add(content)

    result = form.ShowDialog()
    if result != DialogResult.OK:
        return None

    edited = {}
    for kind, name, ctrl, ptype, unit in editors:
        if kind == "bool":
            if ctrl.CheckState == CheckState.Indeterminate:
                continue
            edited[name] = bool(ctrl.Checked)
        else:
            raw = _ada_safe_text(ctrl.Text).strip()
            if raw == "":
                continue
            if ptype == "float":
                try:
                    cleaned = raw.replace(",", ".").split()[0]
                    edited[name] = float(cleaned)
                except Exception:
                    continue
            else:
                edited[name] = raw

    return edited

# Monkey-patch onto the class if available
try:
    WindowParameterManager.edit_parameters_bulk_winforms = edit_parameters_bulk_winforms
except Exception:
    pass