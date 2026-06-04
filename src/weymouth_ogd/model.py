"""Full nonlinear Weymouth formulation.
This module implements the weymouth_ogd formulation, which is a quadratic formulation of the optimal gas dispatch problem. 
This module is designed to be used within a larger framework that handles case loading, result storage,
and command-line interaction, as demonstrated in the main.py file.
The weymouth_ogd class can be instantiated with a load factor and provides a solve method that takes GasNetworkData 
as input and returns a SolveResult containing the optimization outcome, including status, objective value, tables, KPIs, charts, and metadata about the run.
The model is built using Gurobi's Python API, and the formulation includes constraints for supply bounds, mass balance, valve operations, 
and the quadratic Weymouth equations for gas flow. 
The objective function is set to minimize supply costs and load shedding, with a large penalty for unserved demand. 
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

_env_license = Path(sys.prefix) / "gurobi.lic"
if _env_license.exists():
    os.environ.setdefault("GRB_LICENSE_FILE", str(_env_license))

import gurobipy as gp

from ..common.context import GasNetworkData
from ..common.chart import build_charts
from ..common.results import SolveResult, extract_results
from .constraints import build_bounds, build_mass_balance, build_quadratic_weymouth, build_supply_bounds, build_valve_constraints
from .objective import set_objective
from .variables import build_variables


def _objective_value(model: gp.Model) -> float:
    """Return the objective if the model solved."""

    if getattr(model, "SolCount", 0):
        return float(model.ObjVal)
    return float("nan")


@dataclass
class weymouth_ogd:
    """Quadratic Weymouth formulation with bidirectional flow."""

    load_factor: float = 1.0
    name: str = "weymouth_ogd"

    def solve(self, data: GasNetworkData) -> SolveResult:
        model, variables = self._build_model(data)
        model.optimize()
        tables, kpis, solution = extract_results(data, model, variables, self.load_factor)
        objective_value = _objective_value(model)
        status = str(kpis["solve_status"])

        charts = build_charts(data, solution, output_dir=Path(data.metadata["output_dir"]))
        metadata = {
            "load_factor": self.load_factor,
            "formulation": self.name,
            "notes": [
                "Quadratic Weymouth formulation solved as MIQCP.",
                "Bidirectional flow uses big-M direction binaries.",
                "Solved with Gurobi.",
            ],
        }
        return SolveResult(status=status, objective_value=objective_value, tables=tables, kpis=kpis, charts=charts, metadata=metadata, solution=solution)

    def _build_model(self, data: GasNetworkData) -> tuple[gp.Model, dict[str, dict[str, gp.Var]]]:
        model = gp.Model("weymouth_ogd")
        model.Params.OutputFlag = 0
        model.Params.Seed = 1
        model.Params.NonConvex = 2
        variables = build_variables(model, data)
        build_supply_bounds(model, data, variables)
        build_bounds(model, data, variables)
        build_valve_constraints(model, data, variables)
        build_mass_balance(model, data, variables, self.load_factor)
        build_quadratic_weymouth(model, data, variables)
        set_objective(model, data, variables)
        model.update()
        return model, variables
