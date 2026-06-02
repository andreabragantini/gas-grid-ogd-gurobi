"""Run orchestration for cases and formulations.

This module orchestrates the complete pipeline:
  1. Load and validate data
  2. Create and configure formulation
  3. Solve the optimization problem
  4. Extract results and generate artifacts
  5. Write outputs to disk

The main entry point is run_case(), which takes a RunConfig and returns a RunOutcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import sys

from ..formulation_registry import create_formulation
from .context import GasNetworkData, RunConfig, RunOutcome
from .loader import load_case
from .outputs import OutputManager


@dataclass(frozen=True)
class FormulationRun:
    """A formulation run result before artifact writing.
    
    Attributes:
        status: Optimization status (e.g., "OPTIMAL", "SUBOPTIMAL")
        objective_value: Value of the objective function at solution
        tables: Dictionary of output tables (as pandas DataFrames converted to dicts)
        kpis: Dictionary of key performance indicators
        charts: Dictionary mapping chart names to file paths
        metadata: Run metadata (parameters, timestamps, etc.)
    """

    status: str
    objective_value: float
    tables: dict[str, Any]
    kpis: dict[str, Any]
    charts: dict[str, Path]
    metadata: dict[str, Any]


def _print_progress(message: str, verbose: bool = False) -> None:
    """Print a progress message if verbose mode is enabled.
    
    Args:
        message: The message to print
        verbose: Whether to print (default False to suppress non-verbose runs)
    """
    if verbose:
        print(f"  → {message}", file=sys.stderr)


def run_case(config: RunConfig, verbose: bool = False) -> RunOutcome:
    """Load a case, resolve a formulation, solve, and write artifacts.
    
    Complete pipeline:
      1. Load case data from CSV files with schema harmonization
      2. Create formulation instance (quadratic or linear)
      3. Build Gurobi optimization model
      4. Solve using Gurobi solver
      5. Extract results (node pressures, flows, KPIs)
      6. Generate visualizations (network, heatmap)
      7. Write all artifacts to outputs/ directory
    
    Args:
        config: RunConfig specifying case, formulation, and parameters
        verbose: If True, print progress messages to stderr
    
    Returns:
        RunOutcome containing results and artifact paths
    
    Raises:
        FileNotFoundError: If case data directory not found
        ValidationError: If data fails validation checks
        GurobiError: If Gurobi solver fails or returns error status
    """

    # Step 1: Load case data
    _print_progress(f"Loading case data from {config.case}...", verbose)
    data = load_case(config.case, data_roots=config.data_roots, load_factor=config.load_factor)
    _print_progress(f"Loaded: {len(data.nodes)} nodes, {len(data.pipes)} pipes, "
                   f"{len(data.suppliers)} suppliers", verbose)
    
    # Step 2: Create formulation
    _print_progress(f"Creating {config.formulation} formulation...", verbose)
    formulation = create_formulation(config.formulation, config)
    
    # Step 3: Set up output directory
    _print_progress("Setting up output directory...", verbose)
    output_manager = OutputManager(config.output_root, latest_dirname=config.latest_dirname)
    resolved_output = output_manager.resolve(case_name=data.case_name, formulation_name=formulation.name)
    data.metadata["output_dir"] = resolved_output.output_dir.as_posix()
    data.metadata["formulation"] = formulation.name
    data.metadata["load_factor"] = config.load_factor
    _print_progress(f"Output directory: {resolved_output.output_dir}", verbose)
    
    # Step 4: Solve
    _print_progress("Solving optimization model...", verbose)
    solved = formulation.solve(data)
    _print_progress(f"Solver status: {solved.status}", verbose)

    # Step 5: Write artifacts
    _print_progress("Writing artifacts (tables, charts, metadata)...", verbose)
    artifacts = output_manager.write(
        case_name=data.case_name,
        formulation_name=formulation.name,
        tables=solved.tables,
        kpis=solved.kpis,
        metadata=solved.metadata,
        charts=solved.charts,
    )
    _print_progress("Artifacts written successfully", verbose)

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
