"""CLI entrypoint for Optimal Gas Dispatch runs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.common.context import RunConfig
from src.common.loader import list_available_cases
from src.common.runner import run_case


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(description="Run a gas dispatch case.")
    parser.add_argument("--case", default="custom_MP_4nodes", help="Case name to run.")
    parser.add_argument(
        "--formulation",
        default="weymouth_ogd",
        help="Formulation name to run.",
    )
    parser.add_argument(
        "--load-factor",
        type=float,
        default=1.0,
        help="Fraction of the nominal demand to include in the model.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List available cases and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_cases:
        for case in list_available_cases():
            print(case)
        return 0

    config = RunConfig(
        case=args.case,
        formulation=args.formulation,
        data_roots=(Path("data"),),
        output_root=Path("outputs"),
        load_factor=args.load_factor,
    )
    outcome = run_case(config)
    print(outcome.output_dir)
    print(outcome.result.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
