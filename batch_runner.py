"""Batch runner for executing multiple gas dispatch cases.

This module provides utilities to run multiple test cases with different formulations
and parameters in a single invocation. It supports:
  - Running all predefined cases
  - Running selected cases with specific formulations
  - Custom parameter combinations
  - Summary reporting of all runs

Example usage:
    Run all default test scenarios:
        python batch_runner.py

    Run specific cases only:
        python batch_runner.py --cases custom_MP_4nodes ringed_LP_7nodes

    Run with custom load factor:
        python batch_runner.py --load-factor 0.5

    Run a single case (equivalent to main.py):
        python batch_runner.py --cases custom_MP_4nodes --formulations weymouth_ogd

Output:
    A summary report is printed showing status of all runs.
    Individual results are written to outputs/<case>/<formulation>/latest/ as usual.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import datetime
from typing import NamedTuple

from src.common.context import RunConfig
from src.common.loader import list_available_cases
from src.common.runner import run_case


class RunResult(NamedTuple):
    """Result of a single run."""
    case: str
    formulation: str
    load_factor: float
    status: str
    output_dir: Path
    duration_seconds: float


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser for batch operations.
    """
    parser = argparse.ArgumentParser(
        description="Batch runner for gas dispatch cases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_runner.py
      Run all default cases with all formulations.

  python batch_runner.py --cases custom_MP_4nodes
      Run only the custom 4-node case.

  python batch_runner.py --cases ringed_LP_7nodes --formulations weymouth_lp_ogd
      Run the 7-node case with linear formulation only.

  python batch_runner.py --load-factor 0.5
      Run all cases at 50%% load.

  python batch_runner.py --list-scenarios
      List all predefined batch scenarios (if defined).
        """
    )
    
    parser.add_argument(
        "--cases",
        nargs="+",
        help="Specific case(s) to run. If omitted, runs all available cases.",
    )
    parser.add_argument(
        "--formulations",
        nargs="+",
        default=["weymouth_ogd", "weymouth_lp_ogd"],
        choices=["weymouth_ogd", "weymouth_lp_ogd"],
        help="Formulation(s) to use (default: both).",
    )
    parser.add_argument(
        "--load-factor",
        type=float,
        default=1.0,
        help="Demand load factor [0-1] (default: 1.0 = full load).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output for each run.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List predefined batch scenarios and exit.",
    )
    
    return parser


def print_header(title: str) -> None:
    """Print a formatted header.
    
    Args:
        title: The header title to display.
    """
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def get_predefined_scenarios() -> dict[str, dict]:
    """Get predefined batch scenarios.
    
    Returns:
        Dictionary mapping scenario names to their configurations.
    """
    return {
        "quick_test": {
            "cases": ["custom_MP_4nodes"],
            "formulations": ["weymouth_ogd"],
            "load_factor": 0.49,
            "description": "Quick smoke test: single small case at reduced load."
        },
        "small_cases": {
            "cases": ["custom_MP_4nodes", "ringed_LP_7nodes", "ringed_MP_7nodes"],
            "formulations": ["weymouth_ogd", "weymouth_lp_ogd"],
            "load_factor": 1.0,
            "description": "All small test cases with both formulations at full load."
        },
        "linear_verification": {
            "cases": ["ringed_LP_7nodes"],
            "formulations": ["weymouth_lp_ogd"],
            "load_factor": 1.0,
            "description": "Verify linear formulation on small case."
        },
        "full_suite": {
            "cases": ["custom_MP_4nodes", "ringed_LP_7nodes", "ringed_MP_7nodes", "ZUG_1300nodes"],
            "formulations": ["weymouth_ogd", "weymouth_lp_ogd"],
            "load_factor": 1.0,
            "description": "Full test suite: all cases, both formulations, full load."
        },
    }


def run_batch(
    cases: list[str],
    formulations: list[str],
    load_factor: float = 1.0,
    verbose: bool = False,
) -> list[RunResult]:
    """Execute a batch of runs.
    
    Args:
        cases: List of case names to run.
        formulations: List of formulation names to use.
        load_factor: Demand load factor to apply to all runs.
        verbose: Whether to print verbose output.
    
    Returns:
        List of RunResult objects, one per completed run.
    """
    results: list[RunResult] = []
    total_runs = len(cases) * len(formulations)
    run_num = 0

    for case in cases:
        for formulation in formulations:
            run_num += 1
            run_start = datetime.now()
            
            print(f"[{run_num}/{total_runs}] Running {case} + {formulation} "
                  f"(load={load_factor:.0%})...")

            config = RunConfig(
                case=case,
                formulation=formulation,
                data_roots=(Path("data"),),
                output_root=Path("outputs"),
                load_factor=load_factor,
            )

            try:
                outcome = run_case(config)
                duration = (datetime.now() - run_start).total_seconds()

                result = RunResult(
                    case=case,
                    formulation=formulation,
                    load_factor=load_factor,
                    status=outcome.result.status,
                    output_dir=outcome.output_dir,
                    duration_seconds=duration,
                )
                results.append(result)

                status_symbol = "✓" if outcome.result.status == "OPTIMAL" else "✗"
                print(f"   {status_symbol} Status: {outcome.result.status} "
                      f"({duration:.1f}s)")

            except Exception as e:
                duration = (datetime.now() - run_start).total_seconds()
                print(f"   ✗ FAILED: {e}")

                result = RunResult(
                    case=case,
                    formulation=formulation,
                    load_factor=load_factor,
                    status="FAILED",
                    output_dir=Path(""),
                    duration_seconds=duration,
                )
                results.append(result)

    return results


def print_summary(results: list[RunResult]) -> None:
    """Print a summary of all runs.
    
    Args:
        results: List of RunResult objects to summarize.
    """
    print_header("Batch Run Summary")

    # Group by status
    optimal = [r for r in results if r.status == "OPTIMAL"]
    suboptimal = [r for r in results if r.status not in ("OPTIMAL", "FAILED")]
    failed = [r for r in results if r.status == "FAILED"]

    print(f"Total runs:     {len(results)}")
    print(f"Optimal:        {len(optimal)}")
    print(f"Suboptimal:     {len(suboptimal)}")
    print(f"Failed:         {len(failed)}")
    print()

    if optimal:
        print("✓ OPTIMAL runs:")
        for r in optimal:
            print(f"    {r.case:20s} + {r.formulation:15s} ({r.duration_seconds:6.1f}s)")
        print()

    if suboptimal:
        print("~ SUBOPTIMAL runs:")
        for r in suboptimal:
            print(f"    {r.case:20s} + {r.formulation:15s} ({r.status})")
        print()

    if failed:
        print("✗ FAILED runs:")
        for r in failed:
            print(f"    {r.case:20s} + {r.formulation:15s}")
        print()

    total_time = sum(r.duration_seconds for r in results)
    print(f"Total time:     {total_time:.1f}s")
    print()


def main(argv: list[str] | None = None) -> int:
    """Execute batch runner.
    
    Args:
        argv: Command line arguments (defaults to sys.argv[1:] if None).
    
    Returns:
        0 if all runs succeeded, 1 if any failed or errors occurred.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # List scenarios
    if args.list_scenarios:
        print_header("Predefined Batch Scenarios")
        scenarios = get_predefined_scenarios()
        for name, config in scenarios.items():
            print(f"{name:20s}  {config['description']}")
        print()
        return 0

    # Determine which cases to run
    if args.cases:
        cases = args.cases
    else:
        cases = list(list_available_cases())

    print_header("Batch Run Configuration")
    print(f"Start time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cases:          {', '.join(cases)}")
    print(f"Formulations:   {', '.join(args.formulations)}")
    print(f"Load factor:    {args.load_factor:.0%}")
    print(f"Total runs:     {len(cases) * len(args.formulations)}")
    print()

    # Run batch
    results = run_batch(
        cases=cases,
        formulations=args.formulations,
        load_factor=args.load_factor,
        verbose=args.verbose,
    )

    # Print summary
    print_summary(results)

    # Return success only if no failures
    failed_count = sum(1 for r in results if r.status == "FAILED")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
