"""Load and harmonize legacy or canonical gas case datasets.
This module provides the `load_case` function which implements a flexible loading mechanism to read gas network data from CSV files. 
It supports:
  - Multiple data roots for case discovery (e.g., local data directory, shared network location)
  - Multiple candidate filenames for each expected table (e.g., gas_nodes.csv, nodes.csv)
  - Automatic delimiter detection (comma, semicolon, tab)
  - Schema harmonization to convert legacy column names and mixed units into a canonical format
  - Validation of the loaded data against expected constraints (e.g., required columns, logical consistency)
  - Application of a load factor to scale demand values if specified
The main function `load_case` returns a GasNetworkData object containing the harmonized tables and metadata about the loading process. 
It raises informative exceptions if required files are missing or if validation fails.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

from .context import GasNetworkData
from .schema import (
    OPTIONAL_FILES,
    REQUIRED_FILES,
    TABLE_RULES,
    normalize_name,
)
from .validation import ValidationError, validate_case_data


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOTS = (REPO_ROOT / "data",)

_TABLE_FILE_CANDIDATES = {
    "nodes": ("gas_nodes.csv", "nodes.csv", "Nodes.csv"),
    "pipes": ("gas_pipes.csv", "pipes.csv", "Pipes.csv"),
    "suppliers": ("gas_reservoir.csv", "SupplyNG.csv", "suppliers.csv"),
    "loads": ("gas_loads_special.csv", "loads.csv"),
    "valves": ("gas_valves.csv", "valves.csv"),
    "compressors": ("gas_compressors.csv", "compressors.csv"),
}

_UNIT_CONVERTERS = {
    "lengthm": lambda series: series / 1000.0,
    "lkm": lambda series: series,
    "diameterm": lambda series: series * 1000.0,
    "dmm": lambda series: series,
    "pressurepa": lambda series: series / 1000.0,
    "pressurebar": lambda series: series * 100.0,
    "pressurempa": lambda series: series * 1000.0,
}


def _sniff_separator(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"]).delimiter
    except csv.Error:
        return ","


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV using delimiter auto-detection."""

    separator = _sniff_separator(path)
    return pd.read_csv(path, sep=separator)


def _find_case_dir(case_name: str, roots: Iterable[Path]) -> tuple[Path, Path]:
    """Find a case directory in the preferred roots."""

    for root in roots:
        candidate = root / case_name
        if candidate.exists():
            files = {path.name for path in candidate.iterdir() if path.is_file()}
            if any(required in files for required in REQUIRED_FILES):
                return root, candidate
    for root in roots:
        candidate = root / case_name
        if candidate.exists():
            return root, candidate
    raise FileNotFoundError(f"Could not find case '{case_name}' in the configured data roots.")


def _find_file(case_dir: Path, candidates: Iterable[str]) -> Path | None:
    for name in candidates:
        candidate = case_dir / name
        if candidate.exists():
            return candidate
    return None


def _match_column_name(columns: list[str], aliases: Iterable[str]) -> str | None:
    normalized = {normalize_name(column): column for column in columns}
    for alias in aliases:
        match = normalized.get(normalize_name(alias))
        if match is not None:
            return match
    return None


def _convert_if_needed(canonical: str, source_column: str, frame: pd.DataFrame) -> pd.Series:
    normalized_source = normalize_name(source_column)
    if normalized_source in _UNIT_CONVERTERS:
        return _UNIT_CONVERTERS[normalized_source](pd.to_numeric(frame[source_column], errors="coerce"))
    if canonical in {"length_km", "diameter_mm"}:
        return pd.to_numeric(frame[source_column], errors="coerce")
    if canonical in {"p_min_kpa", "p_max_kpa", "to_pressure_kpa", "p_nom_kpa"}:
        return pd.to_numeric(frame[source_column], errors="coerce")
    if canonical in {"q_demand_tcmh", "q_min_tcmh", "q_max_tcmh", "marginal_cost"}:
        return pd.to_numeric(frame[source_column], errors="coerce")
    return frame[source_column]


def _harmonize_table(table_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Harmonize a loaded table to the canonical schema using the defined rules."""
    rules = TABLE_RULES[table_name]
    result = pd.DataFrame(index=frame.index)

    matched_columns: set[str] = set()
    for rule in rules:
        source = _match_column_name(list(frame.columns), rule.aliases)
        if source is None:
            if rule.required:
                raise ValueError(f"Missing required column for {table_name}: {rule.canonical}")
            continue
        matched_columns.add(source)
        result[rule.canonical] = _convert_if_needed(rule.canonical, source, frame)

    for column in frame.columns:
        if column not in matched_columns:
            result[column] = frame[column]

    if table_name == "pipes" and "uid" not in result.columns and {"from_node", "to_node"}.issubset(result.columns):
        result["uid"] = result["from_node"].astype(str) + "->" + result["to_node"].astype(str)

    if table_name == "nodes" and "p_min_kpa" not in result.columns:
        result["p_min_kpa"] = 0.0
    if table_name == "nodes" and "p_max_kpa" not in result.columns and "p_min_kpa" in result.columns:
        result["p_max_kpa"] = result["p_min_kpa"]

    return result


def _empty_table(table_name: str) -> pd.DataFrame:
    columns = [rule.canonical for rule in TABLE_RULES[table_name]]
    return pd.DataFrame(columns=columns)


def _load_table(case_dir: Path, table_name: str, required: bool) -> pd.DataFrame:
    file_path = _find_file(case_dir, _TABLE_FILE_CANDIDATES[table_name])
    if file_path is None:
        if required:
            raise FileNotFoundError(f"Missing required file for {table_name}: {case_dir}")
        return _empty_table(table_name)
    frame = _read_csv(file_path)
    return _harmonize_table(table_name, frame)


def _apply_load_factor(data: GasNetworkData, load_factor: float) -> GasNetworkData:
    """Scale all demand columns by a simple multiplicative factor."""

    factor = float(load_factor)
    if factor == 1.0:
        return data

    if "q_demand_tcmh" in data.nodes.columns:
        data.nodes["q_demand_tcmh"] = pd.to_numeric(data.nodes["q_demand_tcmh"], errors="coerce").fillna(0.0) * factor
    if "q_demand_tcmh" in data.loads.columns:
        data.loads["q_demand_tcmh"] = pd.to_numeric(data.loads["q_demand_tcmh"], errors="coerce").fillna(0.0) * factor
    if "q_tcmh" in data.loads.columns:
        data.loads["q_tcmh"] = pd.to_numeric(data.loads["q_tcmh"], errors="coerce").fillna(0.0) * factor
    return data


def load_case(
    case_name: str,
    data_roots: Iterable[Path] = DEFAULT_DATA_ROOTS,
    load_factor: float = 1.0,
) -> GasNetworkData:
    """Load and validate a case from the configured data roots."""

    source_root, case_dir = _find_case_dir(case_name, data_roots)

    nodes = _load_table(case_dir, "nodes", required=True)
    pipes = _load_table(case_dir, "pipes", required=True)
    suppliers = _load_table(case_dir, "suppliers", required=True)
    loads = _load_table(case_dir, "loads", required=False)
    valves = _load_table(case_dir, "valves", required=False)
    compressors = _load_table(case_dir, "compressors", required=False)

    data = GasNetworkData(
        case_name=case_name,
        source_root=source_root,
        source_case_dir=case_dir,
        nodes=nodes,
        pipes=pipes,
        suppliers=suppliers,
        loads=loads,
        valves=valves,
        compressors=compressors,
        metadata={
            "input_files": sorted(path.name for path in case_dir.iterdir() if path.is_file()),
            "required_files": REQUIRED_FILES,
            "optional_files": OPTIONAL_FILES,
        },
    )
    data = _apply_load_factor(data, load_factor)

    report = validate_case_data(data)
    if not report.is_valid:
        raise ValidationError(report)
    if report.warnings:
        data.metadata["warnings"] = [issue.message for issue in report.warnings]
    return data


def list_available_cases(data_roots: Iterable[Path] = DEFAULT_DATA_ROOTS) -> list[str]:
    """Return all case names discoverable from the configured roots."""

    candidates: set[str] = set()
    for root in data_roots:
        if not root.exists():
            continue
        for case_dir in root.iterdir():
            if not case_dir.is_dir():
                continue
            names = {path.name for path in case_dir.iterdir() if path.is_file()}
            if any(required in names for required in REQUIRED_FILES):
                candidates.add(case_dir.name)
    return sorted(candidates)
