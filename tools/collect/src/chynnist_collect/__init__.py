# SPDX-License-Identifier: GPL-3.0-or-later
"""Collector for Chynnist: turns documents of the Verkhovna Rada open data portal into a Suvii collection."""

__version__ = "0.1.0"

from .convert import Converted, Report, convert
from .styles import Styles
from .tree import ConvertError

__all__ = ["ConvertError", "Converted", "Report", "Styles", "convert"]
