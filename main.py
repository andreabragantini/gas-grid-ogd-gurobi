"""CLI entrypoint for Optimal Gas Dispatch runs.

This module provides a command-line interface to execute gas network optimization
models using different formulations (Weymouth linear or quadratic) on various case
studies. It supports single runs with customizable parameters or batch listing of
available cases.

Example usage:
    Run the default case (custom_MP_4nodes) with weymouth_ogd formulation:
        python main.py

    Run a specific case with a reduced load factor:
        python main.py --case ringed_LP_7nodes --formulation weymouth_lp_ogd --load-factor 0.5

    List all available cases:
        python main.py --list-cases

Output:
    Results are written to outputs/<case_name>/<formulation_name>/latest/ directory
    including: index.html, kpi_snapshot.json, run_metadata.json, and tables/charts subdirectories.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import datetime

from src.common.context import RunConfig
from src.common.loader import list_available_cases
from src.common.runner import run_case


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser for CLI.
    """

    parser = argparse.ArgumentParser(
        description="Optimal Gas Dispatch solver using Gurobi.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --list-cases
      List all available test cases.
  
  python main.py --case custom_MP_4nodes --formulation weymouth_ogd
      Run custom 4-node case with quadratic formulation at full load.
  
  python main.py --case ringed_LP_7nodes --formulation weymouth_lp_ogd --load-factor 0.7
      Run 7-node case with linear formulation at 70%% load.
        """
    )
    parser.add_argument(
        "--case",
        default="custom_MP_4nodes",
        help="Case name to run (default: custom_MP_4nodes). Use --list-cases to see available options.",
    )
    parser.add_argument(
        "--formulation",
        default="weymouth_ogd",
        choices=["weymouth_ogd", "weymouth_lp_ogd"],
        help="Formulation to use (default: weymouth_ogd). "
             "weymouth_ogd: quadratic MIQCP; weymouth_lp_ogd: piecewise linear.",
    )
    parser.add_argument(
        "--load-factor",
        type=float,
        default=1.0,
        help="Demand load factor [0-1]: fraction of nominal demand to include (default: 1.0 = full load).",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List all available test cases and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output showing detailed progress.",
    )
    return parser


def print_section(title: str) -> None:
    """Print a formatted section header.
    
    Args:
        title: The section title to display.
    """
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main(argv: list[str] | None = None) -> int:
    """Execute the CLI.
    
    Handles two main flows:
    1. List available cases: when --list-cases is specified
    2. Run a single case: loads data, resolves formulation, solves, and writes results
    
    Args:
        argv: Command line arguments (defaults to sys.argv[1:] if None).
    
    Returns:
        0 on success, 1 on failure.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_cases:
        print_section("Available Test Cases")
        for case in list_available_cases():
            print(f"  • {case}")
        return 0

    # Build and execute the run configuration
    print_section("Gas Network Optimization Run")
    print(f"Start time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Case:           {args.case}")
    print(f"Formulation:    {args.formulation}")
    print(f"Load factor:    {args.load_factor:.1%}")
    print()

    config = RunConfig(
        case=args.case,
        formulation=args.formulation,
        data_roots=(Path("data"),),
        output_root=Path("outputs"),
        load_factor=args.load_factor,
    )

    try:
        if args.verbose:
            print("Loading case data...")
        outcome = run_case(config)

        print(" # Run Completed")
        print(f"Status:         {outcome.result.status}")
        print(f"Output:         {outcome.output_dir}")
        print(f"Index HTML:     {outcome.artifacts['index']}")
        print()

        return 0

    except Exception as e:
        print_section("Run Failed")
        print(f"Error: {e}")
        print()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
