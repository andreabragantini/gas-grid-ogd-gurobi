"""Variables and helpers for the linearized Weymouth formulation."""

from __future__ import annotations

import math

import gurobipy as gp

from ..common.context import GasNetworkData


def weymouth_constant(pipe_row) -> float:
    """Return the legacy Weymouth constant used by the old code trace."""

    diameter_mm = float(getattr(pipe_row, "diameter_mm", 0.0) or 0.0)
    length_km = float(getattr(pipe_row, "length_km", 0.0) or 0.0)
    if diameter_mm <= 0.0 or length_km <= 0.0:
        return 0.0

    friction = float(getattr(pipe_row, "friction", 0.0) or 0.0)
    if friction <= 0.0:
        friction = 4.0 / (11.18 * diameter_mm ** (1.0 / 6.0)) ** 2

    tb = 273.0
    pb = 101.0
    ta = 300.0
    za = 0.9
    g = 0.6
    e = 0.9
    const = 0.0011493
    return (
        const
        * tb
        / pb
        * diameter_mm ** 2.5
        * e
        / math.sqrt(length_km * g * ta * za * friction)
        / 24.0
        / 1000.0
    )


def pipe_capacity(pipe_row, default_big_m: float) -> float:
    """Return a simple flow cap for a pipe."""

    explicit = float(getattr(pipe_row, "capacity", 0.0) or 0.0)
    if explicit > 0.0:
        return explicit
    return default_big_m


def build_variables(model: gp.Model, data: GasNetworkData) -> dict[str, dict[str, gp.Var]]:
    """Create the decision variables used by the linear formulation."""

    variables: dict[str, dict[str, gp.Var]] = {
        "supply": {},
        "pressure": {},
        "flow": {},
        "valve_flow": {},
        "load_shed": {},
    }

    node_by_uid = {str(row.uid): row for row in data.nodes.itertuples(index=False)}
    supplier_by_uid = {str(row.uid): row for row in data.suppliers.itertuples(index=False)}

    for supplier_uid, row in supplier_by_uid.items():
        lb = float(getattr(row, "q_min_tcmh", 0.0) or 0.0)
        ub = float(getattr(row, "q_max_tcmh", 0.0) or 0.0)
        if ub <= 0.0:
            ub = gp.GRB.INFINITY
        variables["supply"][supplier_uid] = model.addVar(lb=lb, ub=ub, name=f"supply[{supplier_uid}]")

    for node_uid, row in node_by_uid.items():
        lb = float(getattr(row, "p_min_kpa", 0.0) or 0.0)
        ub = float(getattr(row, "p_max_kpa", lb) or lb)
        variables["pressure"][node_uid] = model.addVar(lb=lb, ub=ub, name=f"pressure[{node_uid}]")
        variables["load_shed"][node_uid] = model.addVar(lb=0.0, ub=gp.GRB.INFINITY, name=f"shed[{node_uid}]")

    for pipe_row in data.pipes.itertuples(index=False):
        pipe_uid = str(pipe_row.uid)
        cap = pipe_capacity(pipe_row, default_big_m=10000.0)
        variables["flow"][pipe_uid] = model.addVar(lb=0.0, ub=cap, name=f"flow[{pipe_uid}]")

    for valve_row in data.valves.itertuples(index=False):
        valve_uid = str(valve_row.uid)
        variables["valve_flow"][valve_uid] = model.addVar(lb=0.0, ub=gp.GRB.INFINITY, name=f"valve_flow[{valve_uid}]")

    model.update()
    return variables
