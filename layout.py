# ada_core/layout.py — grid layout calculators for sheet placement (UI-free)
from __future__ import annotations
from typing import List, Sequence, Tuple, Optional, Union
from enum import Enum
from Autodesk.Revit.DB import XYZ  # type: ignore

from ada_core.units import mm_to_ft, FT_PER_MM, FT_PER_MM as _FT_PER_MM

class HAnchor(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"

class VAnchor(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"

def _coerce_anchor(val: Union[str, HAnchor, VAnchor], enum_cls, default):
    if isinstance(val, enum_cls):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        for e in enum_cls:
            if e.value == s:
                return e
    return default

def _sorted_box(p1: XYZ, p2: XYZ) -> Tuple[float, float, float, float]:
    """Return (min_x, max_x, min_y, max_y) in sheet feet coords."""
    return min(p1.X, p2.X), max(p1.X, p2.X), min(p1.Y, p2.Y), max(p1.Y, p2.Y)

def grid_positions_for_area(
    count: int,
    p1: XYZ,
    p2: XYZ,
    sizes_mm: Optional[Sequence[Tuple[float, float]]] = None,
    gap_x_mm: float = 10.0,
    gap_y_mm: float = 10.0,
    max_rows: int = 3,
    max_per_row: int = 6,
    h_anchor: Union[str, HAnchor] = HAnchor.LEFT,
    v_anchor: Union[str, VAnchor] = VAnchor.TOP,
    min_cell_w_mm: float = 20.0,
    min_cell_h_mm: float = 20.0,
) -> List[XYZ]:
    """
    Compute grid positions (sheet coordinates) for placing 'count' view centers inside
    the rectangle defined by p1/p2. 'sizes_mm' is an optional list of (w_mm, h_mm) per view.
    The algorithm packs left-to-right, top-to-bottom (or by anchor), wrapping rows when width is exhausted.
    Returns a list of XYZ centers (length <= count if area is too small).
    """
    if count <= 0:
        return []
    h_anchor = _coerce_anchor(h_anchor, HAnchor, HAnchor.LEFT)
    v_anchor = _coerce_anchor(v_anchor, VAnchor, VAnchor.TOP)

    min_x, max_x, min_y, max_y = _sorted_box(p1, p2)
    avail_w_ft = max(0.0, max_x - min_x)
    avail_h_ft = max(0.0, max_y - min_y)
    avail_w_mm = avail_w_ft / _FT_PER_MM
    avail_h_mm = avail_h_ft / _FT_PER_MM

    # Normalise sizes
    sizes: List[Tuple[float, float]] = []
    if not sizes_mm or len(sizes_mm) == 0:
        sizes = [(max(min_cell_w_mm, 50.0), max(min_cell_h_mm, 50.0))] * count
    else:
        # pad or trim to count
        base = list(sizes_mm)[:count]
        if len(base) < count:
            base += [ (max(min_cell_w_mm, 50.0), max(min_cell_h_mm, 50.0)) ] * (count - len(base))
        sizes = base

    max_h_mm = max(h for _, h in sizes) if sizes else max(min_cell_h_mm, 50.0)

    # Determine number of rows that fit vertically
    rows = 1
    while rows < max_rows:
        total_h = rows * max_h_mm + (rows - 1) * gap_y_mm
        if total_h <= avail_h_mm:
            rows += 1
        else:
            break
    # If we broke because it's too tall, rows is current value; ensure at least 1 and <= max_rows
    if rows > max_rows:
        rows = max_rows

    positions: List[XYZ] = []
    placed = 0
    gap_x_ft = mm_to_ft(gap_x_mm)
    gap_y_ft = mm_to_ft(gap_y_mm)
    row_height_ft = mm_to_ft(max_h_mm)

    # Compute vertical start based on anchor
    if v_anchor == VAnchor.TOP:
        row0_bottom = max_y - row_height_ft
        row_bottom_at = lambda r: row0_bottom - r * (row_height_ft + gap_y_ft)
    elif v_anchor == VAnchor.BOTTOM:
        row0_bottom = min_y
        row_bottom_at = lambda r: row0_bottom + r * (row_height_ft + gap_y_ft)
    else:  # CENTER
        total_h_ft = rows * row_height_ft + (rows - 1) * gap_y_ft
        first_row_bottom = max_y - ((avail_h_ft - total_h_ft) / 2.0 + row_height_ft)
        row_bottom_at = lambda r: first_row_bottom - r * (row_height_ft + gap_y_ft)

    for r in range(rows):
        if placed >= count:
            break
        remaining_w_mm = avail_w_mm
        row_ws: List[float] = []
        row_hs: List[float] = []
        views_in_row = 0
        # pack as many as fit in this row, up to max_per_row
        while placed + views_in_row < count and views_in_row < max_per_row:
            w_mm, h_mm = sizes[placed + views_in_row]
            need = w_mm + (0 if views_in_row == 0 else gap_x_mm)
            if need <= remaining_w_mm and w_mm >= min_cell_w_mm and h_mm >= min_cell_h_mm:
                row_ws.append(w_mm)
                row_hs.append(h_mm)
                remaining_w_mm -= need
                views_in_row += 1
            else:
                break

        if views_in_row == 0:
            # If nothing fits, stop packing further rows
            break

        total_row_w_ft = mm_to_ft(sum(row_ws) + (views_in_row - 1) * gap_x_mm)
        # Horizontal anchoring
        if h_anchor == HAnchor.LEFT:
            start_x = min_x
        elif h_anchor == HAnchor.RIGHT:
            start_x = max_x - total_row_w_ft
        else:  # CENTER
            start_x = min_x + (avail_w_ft - total_row_w_ft) / 2.0

        cur_x = start_x
        row_bottom_y = row_bottom_at(r)
        for i in range(views_in_row):
            w_ft = mm_to_ft(row_ws[i])
            h_ft = mm_to_ft(row_hs[i])
            x = cur_x + w_ft / 2.0
            y = row_bottom_y + h_ft / 2.0
            positions.append(XYZ(x, y, 0.0))
            cur_x += w_ft + gap_x_ft

        placed += views_in_row

    return positions

__all__ = [
    "HAnchor", "VAnchor",
    "grid_positions_for_area",
]
