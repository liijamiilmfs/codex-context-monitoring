"""Domain-agnostic models owned by the chart-rendering provider boundary."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Bar:
    """One labeled numeric value in a generic bar chart."""

    label: str
    value: int


@dataclass(frozen=True, slots=True)
class BarChart:
    """A generic labeled bar chart with a numeric value axis."""

    title: str
    subtitle: str
    value_axis_label: str
    bars: tuple[Bar, ...]


@dataclass(frozen=True, slots=True)
class RenderedChart:
    """In-memory chart content independent of a rendering implementation."""

    media_type: str
    content: bytes
