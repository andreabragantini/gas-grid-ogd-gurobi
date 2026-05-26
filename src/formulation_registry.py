"""Resolve named formulations to concrete implementation objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .common.context import RunConfig
from .weymouth_ogd import weymouth_ogd
from .weymouth_lp_ogd import weymouth_lp_ogd


class Formulation(Protocol):
    """Common interface for dispatch formulations."""

    name: str

    def solve(self, data):  # pragma: no cover - protocol signature only
        """Solve the loaded case and return a structured result."""


@dataclass
class UnsupportedFormulation:
    """Placeholder for formulations that are reserved but not implemented yet."""

    name: str
    reason: str

    def solve(self, data):  # pragma: no cover - intentional failure path
        raise NotImplementedError(self.reason)


def create_formulation(name: str, config: RunConfig) -> Formulation:
    """Return the concrete formulation implementation for the requested name."""

    normalized = name.strip().lower()
    if normalized == "weymouth_ogd":
        return weymouth_ogd(
            load_factor=config.load_factor,
        )
    if normalized == "weymouth_lp_ogd":
        return weymouth_lp_ogd(
            pressure_discretization=config.pressure_discretization,
            load_factor=config.load_factor,
        )
    if normalized == "renouard_mp":
        return UnsupportedFormulation(
            name="renouard_mp",
            reason="Renouard MP is reserved for a future incremental implementation.",
        )
    if normalized == "renouard_lp":
        return UnsupportedFormulation(
            name="renouard_lp",
            reason="Renouard LP is reserved for a future incremental implementation.",
        )
    raise ValueError(f"Unknown formulation: {name}")


def list_formulations() -> tuple[str, ...]:
    """Return the known formulation names."""

    return ("weymouth_ogd", "weymouth_lp_ogd", "renouard_mp", "renouard_lp")
