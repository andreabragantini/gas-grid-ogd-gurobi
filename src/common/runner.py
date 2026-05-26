"""Run orchestration for cases and formulations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..formulation_registry import create_formulation
from .context import GasNetworkData, RunConfig, RunOutcome
from .loader import load_case
from .outputs import OutputManager


@dataclass(frozen=True)
class FormulationRun:
    """A formulation run result before artifact writing."""

    status: str
    objective_value: float
    tables: dict[str, Any]
    kpis: dict[str, Any]
    charts: dict[str, Path]
    metadata: dict[str, Any]


def run_case(config: RunConfig) -> RunOutcome:
    """Load a case, resolve a formulation, solve, and write artifacts."""

    data = load_case(config.case, data_roots=config.data_roots, load_factor=config.load_factor)
    formulation = create_formulation(config.formulation, config)
    output_manager = OutputManager(config.output_root, latest_dirname=config.latest_dirname)
    resolved_output = output_manager.resolve(case_name=data.case_name, formulation_name=formulation.name)
    data.metadata["output_dir"] = resolved_output.output_dir.as_posix()
    data.metadata["formulation"] = formulation.name
    data.metadata["load_factor"] = config.load_factor
    solved = formulation.solve(data)

    artifacts = output_manager.write(
        case_name=data.case_name,
        formulation_name=formulation.name,
        tables=solved.tables,
        kpis=solved.kpis,
        metadata=solved.metadata,
        charts=solved.charts,
    )

    return RunOutcome(
        config=config,
        result=solved,
        output_dir=artifacts.output_dir,
        artifacts={
            "index": artifacts.index_path,
            "metadata": artifacts.metadata_path,
            "kpi": artifacts.kpi_path,
            "tables": artifacts.tables_dir,
            "charts": artifacts.charts_dir,
        },
    )
