"""Shared context objects for gas dispatch runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class RunConfig:
    """Configuration for a single gas dispatch run."""

    case: str
    formulation: str
    data_roots: tuple[Path, ...]
    output_root: Path
    latest_dirname: str = "latest"
    pressure_discretization: int = 5
    load_factor: float = 1.0
    deterministic: bool = True


@dataclass
class GasNetworkData:
    """Canonical data bundle for a case study."""

    case_name: str
    source_root: Path
    source_case_dir: Path
    nodes: pd.DataFrame
    pipes: pd.DataFrame
    suppliers: pd.DataFrame
    loads: pd.DataFrame
    valves: pd.DataFrame
    compressors: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunOutcome:
    """Result of a completed run."""

    config: RunConfig
    result: Any
    output_dir: Path
    artifacts: dict[str, Path]
