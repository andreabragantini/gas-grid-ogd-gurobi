"""Result extraction for the Weymouth formulations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import gurobipy as gp

from ..common.context import GasNetworkData


@dataclass(frozen=True)
class SolveResult:
    """Structured result returned by a formulation run."""

    status: str
    objective_value: float
    tables: dict[str, pd.DataFrame]
    kpis: dict[str, Any]
    charts: dict[str, Any]
    metadata: dict[str, Any]
    solution: dict[str, Any]


def _frame_from_series(values: list[dict[str, Any]], index_name: str) -> pd.DataFrame:
    frame = pd.DataFrame(values)
    if frame.empty:
        return frame
    return frame.set_index(index_name)


def _status_name(status_code: int) -> str:
    if isinstance(status_code, str):
        return status_code
    mapping = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
        gp.GRB.INTERRUPTED: "INTERRUPTED",
        gp.GRB.NUMERIC: "NUMERIC",
        gp.GRB.NODE_LIMIT: "NODE_LIMIT",
        gp.GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
    }
    return mapping.get(int(status_code), str(int(status_code)))


def _value(item: Any) -> float:
    if hasattr(item, "X"):
        return float(item.X)
    if hasattr(item, "x"):
        return float(item.x)
    return float(item)


def extract_results(data: GasNetworkData, model, variables: dict[str, dict[str, Any]], load_factor: float) -> tuple[dict[str, pd.DataFrame], dict[str, Any], dict[str, Any]]:
    """Read solver values into small CSV-ready tables and KPI values."""

    supplies = []
    for row in data.suppliers.itertuples(index=False):
        supplier_id = str(row.uid)
        supplies.append(
            {
                "uid": supplier_id,
                "node_id": str(getattr(row, "node_id", "")),
                "supply": _value(variables["supply"][supplier_id]),
            }
        )

    pressures = []
    for row in data.nodes.itertuples(index=False):
        node_id = str(row.uid)
        pressures.append(
            {
                "uid": node_id,
                "pressure_kpa": _value(variables["pressure"][node_id]),
                "demand_tcmh": float(getattr(row, "q_demand_tcmh", 0.0) or 0.0),
                "load_shed": _value(variables["load_shed"][node_id]),
            }
        )

    flows = []
    valve_flows = []
    q_plus = []
    q_minus = []
    direction = []
    for row in data.pipes.itertuples(index=False):
        pipe_id = str(row.uid)
        flows.append({"uid": pipe_id, "flow": _value(variables["flow"][pipe_id])})
        q_plus.append({"uid": pipe_id, "q_plus": _value(variables["q_plus"][pipe_id])})
        q_minus.append({"uid": pipe_id, "q_minus": _value(variables["q_minus"][pipe_id])})
        direction.append({"uid": pipe_id, "direction": _value(variables["direction"][pipe_id])})

    for row in data.valves.itertuples(index=False):
        valve_id = str(row.uid)
        valve_flows.append({"uid": valve_id, "flow": _value(variables["valve_flow"][valve_id])})

    total_demand = float((pd.to_numeric(data.nodes.get("q_demand_tcmh", pd.Series(dtype=float)), errors="coerce").fillna(0.0)).sum())
    total_supply = float(sum(item["supply"] for item in supplies))
    total_shed = float(sum(item["load_shed"] for item in pressures))

    tables = {
        "supply": _frame_from_series(supplies, "uid"),
        "node_pressure": _frame_from_series(pressures, "uid"),
        "pipe_flow": _frame_from_series(flows, "uid"),
        "valve_flow": _frame_from_series(valve_flows, "uid"),
        "q_plus": _frame_from_series(q_plus, "uid"),
        "q_minus": _frame_from_series(q_minus, "uid"),
        "direction": _frame_from_series(direction, "uid"),
    }

    kpis = {
        "case": data.case_name,
        "load_factor": float(load_factor),
        "objective_value": float(model.ObjVal),
        "solve_status": _status_name(model.Status),
        "total_demand": total_demand,
        "total_supply": total_supply,
        "total_load_shed": total_shed,
    }

    solution = {
        "status": _status_name(model.Status),
        "objective_value": float(model.ObjVal),
        "total_demand": total_demand,
        "total_supply": total_supply,
        "total_load_shed": total_shed,
        "supplies": supplies,
        "pressures": pressures,
        "flows": flows,
        "valve_flows": valve_flows,
        "q_plus": q_plus,
        "q_minus": q_minus,
        "direction": direction,
    }

    return tables, kpis, solution
