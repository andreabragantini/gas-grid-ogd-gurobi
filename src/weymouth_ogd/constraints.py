"""Constraint builders for the full nonlinear Weymouth formulation."""

from __future__ import annotations

from collections import defaultdict

import gurobipy as gp

from ..common.context import GasNetworkData
from .variables import pipe_capacity, weymouth_constant


def _node_maps(data: GasNetworkData) -> tuple[dict[str, float], dict[str, float]]:
    p_min = {}
    p_max = {}
    for row in data.nodes.itertuples(index=False):
        node_id = str(row.uid)
        p_min[node_id] = float(getattr(row, "p_min_kpa", 0.0) or 0.0)
        p_max[node_id] = float(getattr(row, "p_max_kpa", p_min[node_id]) or p_min[node_id])
    return p_min, p_max


def _supplier_map(data: GasNetworkData) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for row in data.suppliers.itertuples(index=False):
        node_id = str(getattr(row, "node_id", ""))
        mapping[node_id].append(str(row.uid))
    return mapping


def _pipe_maps(data: GasNetworkData) -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    from_node = {}
    to_node = {}
    capacity = {}
    for row in data.pipes.itertuples(index=False):
        pipe_id = str(row.uid)
        from_node[pipe_id] = str(row.from_node)
        to_node[pipe_id] = str(row.to_node)
        capacity[pipe_id] = pipe_capacity(row, default_big_m=10000.0)
    return from_node, to_node, capacity


def build_mass_balance(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]], load_factor: float) -> None:
    """Add nodal mass balance constraints."""

    suppliers_at_node = _supplier_map(data)
    for row in data.nodes.itertuples(index=False):
        node_id = str(row.uid)
        demand = float(getattr(row, "q_demand_tcmh", 0.0) or 0.0)
        inflow = []
        outflow = []
        for pipe_row in data.pipes.itertuples(index=False):
            pipe_id = str(pipe_row.uid)
            if str(pipe_row.from_node) == node_id:
                outflow.append(variables["flow"][pipe_id])
            if str(pipe_row.to_node) == node_id:
                inflow.append(variables["flow"][pipe_id])
        for valve_row in data.valves.itertuples(index=False):
            valve_id = str(valve_row.uid)
            if str(valve_row.from_node) == node_id:
                outflow.append(variables["valve_flow"][valve_id])
            if str(valve_row.to_node) == node_id:
                inflow.append(variables["valve_flow"][valve_id])
        model.addConstr(
            gp.quicksum(variables["supply"][uid] for uid in suppliers_at_node.get(node_id, []))
            + variables["load_shed"][node_id]
            == demand + gp.quicksum(outflow) - gp.quicksum(inflow),
            name=f"mass_balance[{node_id}]",
        )


def build_bounds(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]]) -> None:
    """Add pressure and bidirectional flow bounds."""

    p_min, p_max = _node_maps(data)
    for node_id in variables["pressure"]:
        model.addConstr(variables["pressure"][node_id] >= p_min[node_id], name=f"pmin[{node_id}]")
        model.addConstr(variables["pressure"][node_id] <= p_max[node_id], name=f"pmax[{node_id}]")

    for pipe_row in data.pipes.itertuples(index=False):
        pipe_id = str(pipe_row.uid)
        cap = pipe_capacity(pipe_row, default_big_m=10000.0)
        model.addConstr(variables["q_plus"][pipe_id] <= cap * variables["direction"][pipe_id], name=f"qplus_cap[{pipe_id}]")
        model.addConstr(variables["q_minus"][pipe_id] <= cap * (1 - variables["direction"][pipe_id]), name=f"qminus_cap[{pipe_id}]")
        model.addConstr(variables["flow"][pipe_id] == variables["q_plus"][pipe_id] - variables["q_minus"][pipe_id], name=f"flow_def[{pipe_id}]")


def build_supply_bounds(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]]) -> None:
    """Keep the supply variables inside reservoir limits."""

    for row in data.suppliers.itertuples(index=False):
        supplier_id = str(row.uid)
        if supplier_id not in variables["supply"]:
            continue
        lb = float(getattr(row, "q_min_tcmh", 0.0) or 0.0)
        ub = float(getattr(row, "q_max_tcmh", 0.0) or 0.0)
        model.addConstr(variables["supply"][supplier_id] >= lb, name=f"supply_min[{supplier_id}]")
        if ub > 0.0:
            model.addConstr(variables["supply"][supplier_id] <= ub, name=f"supply_max[{supplier_id}]")


def build_valve_constraints(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]]) -> None:
    """Pin the downstream pressure for each valve."""

    for row in data.valves.itertuples(index=False):
        valve_id = str(row.uid)
        to_node = str(row.to_node)
        to_pressure = float(getattr(row, "to_pressure_kpa", 0.0) or 0.0)
        if to_pressure > 0.0 and to_node in variables["pressure"]:
            model.addConstr(variables["pressure"][to_node] == to_pressure, name=f"valve_pressure[{valve_id}]")


def build_quadratic_weymouth(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]]) -> None:
    """Add the exact quadratic Weymouth constraints."""

    from_node, to_node, _ = _pipe_maps(data)
    kmu = {str(row.uid): weymouth_constant(row) for row in data.pipes.itertuples(index=False)}
    big_m = 10000.0
    model.Params.NonConvex = 2

    for pipe_id in variables["flow"]:
        i = from_node[pipe_id]
        j = to_node[pipe_id]
        k2 = kmu[pipe_id] ** 2
        model.addQConstr(
            variables["q_plus"][pipe_id] * variables["q_plus"][pipe_id]
            + k2 * variables["pressure"][j] * variables["pressure"][j]
            <= k2 * variables["pressure"][i] * variables["pressure"][i]
            + big_m * (1 - variables["direction"][pipe_id]),
            name=f"weymouth_plus[{pipe_id}]",
        )
        model.addQConstr(
            variables["q_minus"][pipe_id] * variables["q_minus"][pipe_id]
            + k2 * variables["pressure"][i] * variables["pressure"][i]
            <= k2 * variables["pressure"][j] * variables["pressure"][j]
            + big_m * variables["direction"][pipe_id],
            name=f"weymouth_minus[{pipe_id}]",
        )
