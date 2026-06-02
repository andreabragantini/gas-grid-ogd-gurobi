"""Validation helpers for harmonized gas network data.
This module provides functions to validate the loaded gas network data against
the expected canonical schema and logical constraints. It checks for:
  - Presence of required columns in each table
  - Uniqueness of identifiers (e.g., node UIDs, pipe UIDs)
  - Logical consistency (e.g., p_min_kpa <= p_max_kpa for nodes)
  - Referential integrity (e.g., pipes reference existing nodes)
  - Network connectivity (e.g., no isolated nodes or self-loops)
The main function `validate_case_data` returns a ValidationReport summarizing any issues found, which can be used to raise a ValidationError if critical errors are present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from .context import GasNetworkData


@dataclass(frozen=True)
class ValidationIssue:
    """A validation issue raised or reported during case loading."""

    level: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Summary of validation results."""

    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


class ValidationError(ValueError):
    """Raised when a loaded case violates required constraints."""

    def __init__(self, report: ValidationReport) -> None:
        super().__init__("\n".join(issue.message for issue in report.errors))
        self.report = report


def _missing_columns(frame, required: Iterable[str]) -> list[str]:
    return [column for column in required if column not in frame.columns]


def validate_case_data(data: GasNetworkData) -> ValidationReport:
    """Validate canonical tables and network connectivity."""

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if data.nodes.empty:
        errors.append(ValidationIssue("error", "The nodes table is empty."))
    if data.pipes.empty:
        errors.append(ValidationIssue("error", "The pipes table is empty."))
    if data.suppliers.empty:
        warnings.append(ValidationIssue("warning", "The suppliers table is empty."))

    for table_name, frame, required in (
        ("nodes", data.nodes, ("uid", "p_min_kpa", "p_max_kpa")),
        ("pipes", data.pipes, ("uid", "from_node", "to_node")),
        ("suppliers", data.suppliers, ("uid", "node_id", "q_max_tcmh")),
    ):
        missing = _missing_columns(frame, required)
        if missing:
            errors.append(
                ValidationIssue(
                    "error",
                    f"{table_name} is missing required columns: {', '.join(sorted(missing))}.",
                )
            )

    if "uid" in data.nodes.columns and data.nodes["uid"].duplicated().any():
        errors.append(ValidationIssue("error", "Duplicate node UIDs were found."))
    if "uid" in data.pipes.columns and data.pipes["uid"].duplicated().any():
        errors.append(ValidationIssue("error", "Duplicate pipe UIDs were found."))
    if "uid" in data.suppliers.columns and data.suppliers["uid"].duplicated().any():
        errors.append(ValidationIssue("error", "Duplicate supplier UIDs were found."))

    if {"p_min_kpa", "p_max_kpa"}.issubset(data.nodes.columns):
        invalid = data.nodes[data.nodes["p_min_kpa"] > data.nodes["p_max_kpa"]]
        if not invalid.empty:
            errors.append(ValidationIssue("error", "At least one node has p_min_kpa > p_max_kpa."))

    known_nodes = set(data.nodes["uid"].astype(str)) if "uid" in data.nodes.columns else set()
    for table_name, frame, column in (
        ("pipes", data.pipes, "from_node"),
        ("pipes", data.pipes, "to_node"),
        ("suppliers", data.suppliers, "node_id"),
        ("loads", data.loads, "node_id"),
        ("valves", data.valves, "from_node"),
        ("valves", data.valves, "to_node"),
        ("compressors", data.compressors, "from_node"),
        ("compressors", data.compressors, "to_node"),
    ):
        if column not in frame.columns or frame.empty:
            continue
        unknown = sorted({str(value) for value in frame[column] if str(value) not in known_nodes})
        if unknown:
            errors.append(
                ValidationIssue(
                    "error",
                    f"{table_name} references unknown nodes in {column}: {', '.join(unknown)}.",
                )
            )

    if {"from_node", "to_node"}.issubset(data.pipes.columns):
        self_loops = data.pipes[data.pipes["from_node"] == data.pipes["to_node"]]
        if not self_loops.empty:
            errors.append(ValidationIssue("error", "At least one pipe connects a node to itself."))

    if "uid" in data.nodes.columns and "from_node" in data.pipes.columns and "to_node" in data.pipes.columns:
        graph = nx.Graph()
        graph.add_nodes_from(data.nodes["uid"].astype(str))
        graph.add_edges_from(
            (str(row.from_node), str(row.to_node)) for row in data.pipes.itertuples(index=False)
        )
        if graph.number_of_nodes() > 0 and nx.number_connected_components(graph) > 1:
            warnings.append(
                ValidationIssue(
                    "warning",
                    "The network contains more than one connected component.",
                )
            )

    return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

