"""Linearized Weymouth formulation."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

_env_license = Path(sys.prefix) / "gurobi.lic"
if _env_license.exists():
    os.environ.setdefault("GRB_LICENSE_FILE", str(_env_license))

import gurobipy as gp

from ..common.context import GasNetworkData
from .chart import build_charts
from .constraints import build_bounds, build_mass_balance, build_piecewise_weymouth, build_supply_bounds, build_valve_constraints
from .objective import set_objective
from .results import SolveResult, extract_results
from .variables import build_variables


def _objective_value(model: gp.Model) -> float:
    if getattr(model, "SolCount", 0):
        return float(model.ObjVal)
    return float("nan")


def _allocate_supplies(supplier_rows, total_demand: float) -> list[dict[str, float]]:
    if not supplier_rows:
        return []
    capacities = [max(0.0, float(getattr(row, "q_max_tcmh", 0.0))) for row in supplier_rows]
    capacity_total = sum(capacities)
    target = min(total_demand, capacity_total if capacity_total > 0.0 else total_demand)
    if capacity_total <= 0.0:
        equal_share = target / len(supplier_rows) if supplier_rows else 0.0
        return [{"uid": str(row.uid), "supply": float(equal_share)} for row in supplier_rows]
    allocations: list[dict[str, float]] = []
    for row, capacity in zip(supplier_rows, capacities):
        supply = target * (capacity / capacity_total)
        allocations.append({"uid": str(row.uid), "supply": float(min(supply, capacity))})
    return allocations


def _compute_supply_cost(supplier_rows, supplies: list[dict[str, float]]) -> float:
    cost_lookup = {str(row.uid): float(getattr(row, "marginal_cost", getattr(row, "cost", 1.0))) for row in supplier_rows}
    return float(sum(item["supply"] * cost_lookup.get(item["uid"], 1.0) for item in supplies))


def _build_fallback_solution(data: GasNetworkData, load_factor: float) -> dict[str, Any]:
    total_demand = float(data.nodes.get("q_demand_tcmh", pd.Series(dtype=float)).fillna(0.0).sum())
    supplier_rows = list(data.suppliers.itertuples(index=False))
    supplies = _allocate_supplies(supplier_rows, total_demand)
    total_supply = float(sum(item["supply"] for item in supplies))
    unserved = max(0.0, total_demand - total_supply)
    supply_cost = _compute_supply_cost(supplier_rows, supplies)

    pressures = [
        {
            "uid": str(row.uid),
            "pressure_kpa": float((float(getattr(row, "p_min_kpa", 0.0)) + float(getattr(row, "p_max_kpa", 0.0))) / 2.0),
            "demand_tcmh": float(getattr(row, "q_demand_tcmh", 0.0) or 0.0),
            "load_shed": 0.0,
        }
        for row in data.nodes.itertuples(index=False)
    ]
    if unserved > 0.0 and pressures:
        per_node_shed = unserved / len(pressures)
        for item in pressures:
            item["load_shed"] = per_node_shed

    flows = [{"uid": str(row.uid), "flow": 0.0} for row in data.pipes.itertuples(index=False)]
    valve_flows = [{"uid": str(row.uid), "flow": 0.0} for row in data.valves.itertuples(index=False)]
    objective_value = supply_cost + 1_000_000.0 * unserved
    return {
        "status": "FALLBACK_SIZE_LIMIT",
        "objective_value": objective_value,
        "total_demand": total_demand,
        "total_supply": total_supply,
        "total_load_shed": unserved,
        "supplies": supplies,
        "pressures": pressures,
        "flows": flows,
        "valve_flows": valve_flows,
    }


def _fallback_run(data: GasNetworkData, load_factor: float) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float, str]:
    solution = _build_fallback_solution(data, load_factor)
    dummy_model = SimpleNamespace(Status="FALLBACK_SIZE_LIMIT", ObjVal=solution["objective_value"])
    numeric_variables = {
        "supply": {item["uid"]: item["supply"] for item in solution["supplies"]},
        "pressure": {item["uid"]: item["pressure_kpa"] for item in solution["pressures"]},
        "flow": {item["uid"]: item["flow"] for item in solution["flows"]},
        "valve_flow": {item["uid"]: item["flow"] for item in solution["valve_flows"]},
        "load_shed": {item["uid"]: item["load_shed"] for item in solution["pressures"]},
    }
    tables, kpis, solution_data = extract_results(data, dummy_model, numeric_variables, load_factor)
    kpis["solve_status"] = "FALLBACK_SIZE_LIMIT"
    kpis["total_load_shed"] = solution["total_load_shed"]
    kpis["total_supply"] = solution["total_supply"]
    kpis["objective_value"] = solution["objective_value"]
    solution_data["status"] = "FALLBACK_SIZE_LIMIT"
    solution_data["objective_value"] = solution["objective_value"]
    solution_data["total_load_shed"] = solution["total_load_shed"]
    return tables, kpis, solution_data, solution["objective_value"], "FALLBACK_SIZE_LIMIT"


@dataclass
class weymouth_lp_ogd:
    """Linear Weymouth formulation with mono-direction flow."""

    pressure_discretization: int = 5
    load_factor: float = 1.0
    name: str = "weymouth_lp_ogd"

    def solve(self, data: GasNetworkData) -> SolveResult:
        if len(data.nodes) + len(data.pipes) > 1000:
            tables, kpis, solution, objective_value, status = _fallback_run(data, self.load_factor)
        else:
            try:
                model, variables = self._build_model(data)
                model.optimize()
                tables, kpis, solution = extract_results(data, model, variables, self.load_factor)
                objective_value = _objective_value(model)
                status = str(kpis["solve_status"])
            except gp.GurobiError:
                tables, kpis, solution, objective_value, status = _fallback_run(data, self.load_factor)

        charts = build_charts(data, solution, output_dir=Path(data.metadata["output_dir"]))
        metadata = {
            "pressure_discretization": self.pressure_discretization,
            "load_factor": self.load_factor,
            "formulation": self.name,
            "notes": [
                "Linear Weymouth approximation via tangent planes.",
                "Mono-direction flow is assumed.",
                status if status.startswith("FALLBACK") else "Solved with Gurobi.",
            ],
        }
        return SolveResult(status=status, objective_value=objective_value, tables=tables, kpis=kpis, charts=charts, metadata=metadata, solution=solution)

    def _build_model(self, data: GasNetworkData) -> tuple[gp.Model, dict[str, dict[str, gp.Var]]]:
        model = gp.Model("weymouth_lp_ogd")
        model.Params.OutputFlag = 0
        model.Params.Seed = 1
        variables = build_variables(model, data)
        build_supply_bounds(model, data, variables)
        build_bounds(model, data, variables)
        build_valve_constraints(model, data, variables)
        build_mass_balance(model, data, variables, self.load_factor)
        build_piecewise_weymouth(model, data, variables, self.pressure_discretization)
        set_objective(model, data, variables)
        model.update()
        return model, variables
