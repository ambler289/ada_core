#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ada_core.text
Text utilities shared across ADa tools.
"""

from typing import Optional

def convert_case(txt: Optional[str], mode: str) -> Optional[str]:
    """
    Convert text according to mode: 'lowercase', 'UPPERCASE', 'Title Case'.
    Simple and predictable; swap for a smarter titlecasing later if needed.
    """
    if txt is None:
        return txt

    if mode == "lowercase":
        return txt.lower()
    if mode == "UPPERCASE":
        return txt.upper()
    if mode == "Title Case":
        return txt.title()

    return txt
