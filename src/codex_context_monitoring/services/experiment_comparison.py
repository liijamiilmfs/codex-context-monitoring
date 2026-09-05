"""Pure token comparisons for validated controlled experiments."""

from fractions import Fraction

from codex_context_monitoring.experiment_models import (
    ContextReading,
    Experiment,
    ExperimentComparison,
    PercentageWarning,
    SurfaceStatistics,
)


def compare_experiment(experiment: Experiment) -> ExperimentComparison:
    """Keep surfaces separate; flag display discrepancies without changing evidence."""
    desktop = _statistics(experiment.desktop)
    cli = _statistics(experiment.cli)
    warnings: list[PercentageWarning] = []
    for surface, readings in (("Desktop", experiment.desktop), ("CLI", experiment.cli)):
        for number, item in enumerate(readings, 1):
            calculated = 100 * (1 - Fraction(item.used.value, item.capacity.value))
            if abs(item.percentage_left - calculated) > 1:
                warnings.append(
                    PercentageWarning(
                        surface, number, item.line, item.percentage_left, calculated
                    )
                )
    return ExperimentComparison(
        experiment,
        desktop,
        cli,
        desktop.average - cli.average,
        desktop.approximate or cli.approximate,
        tuple(warnings),
    )


def _statistics(readings: tuple[ContextReading, ...]) -> SurfaceStatistics:
    values = tuple(item.used.value for item in readings)
    return SurfaceStatistics(
        count=len(values),
        average=Fraction(sum(values), len(values)),
        minimum=min(values),
        maximum=max(values),
        approximate=any(item.used.rounded for item in readings),
        resolution=max(item.used.resolution for item in readings),
    )
