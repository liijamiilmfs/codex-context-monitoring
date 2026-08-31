"""Application-owned chart-rendering abstraction."""

from typing import Protocol, runtime_checkable

from codex_context_monitoring.chart_models import BarChart, RenderedChart


@runtime_checkable
class ChartRenderer(Protocol):
    """Render a provider-owned generic chart without filesystem I/O."""

    def render(self, chart: BarChart) -> RenderedChart:
        """Return in-memory output for a generic chart."""
