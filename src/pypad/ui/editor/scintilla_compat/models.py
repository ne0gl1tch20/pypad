from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FoldRegion:
    start: int
    end: int
    level: int


@dataclass
class ColumnBlock:
    line_lo: int
    line_hi: int
    col_lo: int
    col_hi: int


@dataclass
class HotspotRange:
    start: int
    end: int
    payload: str = ""


@dataclass
class IndicatorRange:
    start: int
    end: int
    payload: str = ""
    value: int = 0
