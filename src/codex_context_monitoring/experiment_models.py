"""Immutable application data for a manually controlled experiment."""

from dataclasses import dataclass
from datetime import date
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class ExperimentMetadata:
    date: date
    model: str
    reasoning: str
    operating_system: str
    desktop_version: str
    cli_version: str
    conditions: str
    summary: str


@dataclass(frozen=True, slots=True)
class TokenAmount:
    """Normalized count and display increment; K notation remains approximate."""

    value: int
    rounded: bool
    resolution: int


@dataclass(frozen=True, slots=True)
class ContextReading:
    original: str
    line: int
    used: TokenAmount
    capacity: TokenAmount
    percentage_left: Fraction


@dataclass(frozen=True, slots=True)
class Experiment:
    metadata: ExperimentMetadata
    desktop: tuple[ContextReading, ...]
    cli: tuple[ContextReading, ...]


@dataclass(frozen=True, slots=True)
class SurfaceStatistics:
    count: int
    average: Fraction
    minimum: int
    maximum: int
    approximate: bool
    resolution: int


@dataclass(frozen=True, slots=True)
class PercentageWarning:
    surface: str
    reading_number: int
    line: int
    displayed: Fraction
    calculated: Fraction


@dataclass(frozen=True, slots=True)
class ExperimentComparison:
    experiment: Experiment
    desktop: SurfaceStatistics
    cli: SurfaceStatistics
    difference: Fraction
    difference_approximate: bool
    warnings: tuple[PercentageWarning, ...]
