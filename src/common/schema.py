"""Canonical schema and alias definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


def normalize_name(value: str) -> str:
    """Normalize a column or file name for lookup."""

    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


@dataclass(frozen=True)
class ColumnRule:
    """Describe how a canonical column can be matched and normalized."""

    canonical: str
    aliases: tuple[str, ...]
    required: bool = False
    converter: Callable[[pd.Series], pd.Series] | None = None


NODE_RULES = (
    ColumnRule("uid", ("uid", "id", "nodeid", "node", "name"), True),
    ColumnRule("label", ("label", "node", "name")),
    ColumnRule("p_min_kpa", ("prmin", "pmin", "p_min", "minpressure", "pressuremin")),
    ColumnRule("p_max_kpa", ("prmax", "pmax", "p_max", "maxpressure", "pressuremax", "h", "pnom")),
    ColumnRule("q_demand_tcmh", ("qdemand", "q_tcmh", "demand", "load")),
    ColumnRule("x", ("gixx", "x")),
    ColumnRule("y", ("gixy", "y")),
)

PIPE_RULES = (
    ColumnRule("uid", ("uid", "id", "pipeid")),
    ColumnRule("from_node", ("fromnode", "fromuid", "fromid", "from_node"), True),
    ColumnRule("to_node", ("tonode", "touid", "toid", "to_node"), True),
    ColumnRule(
        "length_km",
        ("lengthkm", "length", "lkm", "l_km", "length_m", "lm"),
    ),
    ColumnRule(
        "diameter_mm",
        ("diametermm", "diameter", "dmm", "d_mm", "diameter_m", "dm"),
    ),
    ColumnRule("friction", ("friction", "ff")),
    ColumnRule("ss_constant", ("ssconstant", "ss_constant")),
    ColumnRule("capacity", ("capacity", "qmax", "q_max")),
    ColumnRule("pressure_level", ("pressurelevel", "pressurelevelkpa", "p_n", "pn")),
    ColumnRule("u", ("u",)),
    ColumnRule("zeta", ("zeta", "z", "zeta")),
    ColumnRule("sound", ("sound", "soundms")),
    ColumnRule("directionality", ("directionality", "type", "direction", "flag")),
)

SUPPLIER_RULES = (
    ColumnRule("uid", ("uid", "id"), True),
    ColumnRule("node_id", ("origin", "fromuid", "fromnode", "nodeid", "node_id", "from_id")),
    ColumnRule("q_min_tcmh", ("qmin", "q_min")),
    ColumnRule("q_max_tcmh", ("capacity", "qmax", "q_max")),
    ColumnRule("marginal_cost", ("cost", "marginalcost", "marginal_cost")),
)

LOAD_RULES = (
    ColumnRule("uid", ("uid", "id"), True),
    ColumnRule("node_id", ("nodeid", "node_id", "origin")),
    ColumnRule("netwid", ("netwid", "networkid", "network")),
    ColumnRule("p_nom_kpa", ("pnom", "p_nom", "pressurenominal", "pressure")),
    ColumnRule("q_demand_tcmh", ("qdemand", "q_tcmh", "demand", "load")),
    ColumnRule("x", ("gixx", "x")),
    ColumnRule("y", ("gixy", "y")),
)

VALVE_RULES = (
    ColumnRule("uid", ("uid", "id"), True),
    ColumnRule("from_node", ("fromnode", "fromuid", "from_node"), True),
    ColumnRule("to_node", ("tonode", "touid", "to_node"), True),
    ColumnRule("to_pressure_kpa", ("topressure", "pressure", "p", "to_pressure")),
)

COMPRESSOR_RULES = (
    ColumnRule("from_node", ("fromnode", "fromuid", "from_node"), True),
    ColumnRule("to_node", ("tonode", "touid", "to_node"), True),
    ColumnRule("ratio_min", ("ratiomin", "ratio_min")),
    ColumnRule("ratio_max", ("ratiomax", "ratio_max")),
    ColumnRule("power_coeff", ("powercoeff", "power_coeff")),
)


TABLE_RULES = {
    "nodes": NODE_RULES,
    "pipes": PIPE_RULES,
    "suppliers": SUPPLIER_RULES,
    "loads": LOAD_RULES,
    "valves": VALVE_RULES,
    "compressors": COMPRESSOR_RULES,
}


REQUIRED_FILES = ("gas_nodes.csv", "gas_pipes.csv", "gas_reservoir.csv")
OPTIONAL_FILES = ("gas_loads_special.csv", "gas_valves.csv", "gas_compressors.csv")
