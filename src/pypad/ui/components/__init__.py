"""Expose reusable accessibility-first UI building blocks used across PyPad.

This package groups small, theme-friendly widgets that help feature dialogs and
editor surfaces stay visually consistent without copying layout or accessibility
boilerplate into each workflow module.
"""

from .banner_widget import BannerWidget

__all__ = ["BannerWidget"]
