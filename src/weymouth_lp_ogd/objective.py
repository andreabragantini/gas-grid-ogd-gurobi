"""Objective builder for the Weymouth formulations."""

from __future__ import annotations

import gurobipy as gp

from ..common.context import GasNetworkData


def set_objective(model: gp.Model, data: GasNetworkData, variables: dict[str, dict[str, gp.Var]]) -> None:
    """Minimize supply cost plus a tiny pressure regularization term."""

    supply_terms = []
    for row in data.suppliers.itertuples(index=False):
        supplier_id = str(row.uid)
        cost = float(getattr(row, "marginal_cost", getattr(row, "cost", 1.0)) or 1.0)
        supply_terms.append(cost * variables["supply"][supplier_id])

    pressure_terms = []
    for row in data.pipes.itertuples(index=False):
        i = str(row.from_node)
        j = str(row.to_node)
        pressure_terms.append(variables["pressure"][i] - variables["pressure"][j])

    shed_penalty = []
    for row in data.nodes.itertuples(index=False):
        node_id = str(row.uid)
        shed_penalty.append(1_000_000.0 * variables["load_shed"][node_id])

    model.setObjective(
        gp.quicksum(supply_terms) + 0.001 * gp.quicksum(pressure_terms) + gp.quicksum(shed_penalty),
        gp.GRB.MINIMIZE,
    )
