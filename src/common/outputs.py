"""Artifact-first output handling for gas dispatch runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class OutputArtifacts:
    """Resolved artifact paths for a run."""

    output_dir: Path
    tables_dir: Path
    charts_dir: Path
    kpi_path: Path
    metadata_path: Path
    index_path: Path


class OutputManager:
    """Write deterministic run artifacts to the configured output root."""

    def __init__(self, output_root: Path, latest_dirname: str = "latest") -> None:
        self.output_root = output_root
        self.latest_dirname = latest_dirname

    def resolve(self, case_name: str, formulation_name: str) -> OutputArtifacts:
        output_dir = self.output_root / case_name / formulation_name / self.latest_dirname
        tables_dir = output_dir / "tables"
        charts_dir = output_dir / "charts"
        return OutputArtifacts(
            output_dir=output_dir,
            tables_dir=tables_dir,
            charts_dir=charts_dir,
            kpi_path=output_dir / "kpi_snapshot.json",
            metadata_path=output_dir / "run_metadata.json",
            index_path=output_dir / "index.html",
        )

    def write(
        self,
        case_name: str,
        formulation_name: str,
        tables: Mapping[str, pd.DataFrame],
        kpis: Mapping[str, Any],
        metadata: Mapping[str, Any],
        charts: Mapping[str, Path] | None = None,
    ) -> OutputArtifacts:
        artifacts = self.resolve(case_name, formulation_name)
        artifacts.tables_dir.mkdir(parents=True, exist_ok=True)
        artifacts.charts_dir.mkdir(parents=True, exist_ok=True)

        table_links: list[tuple[str, str]] = []
        for name in sorted(tables):
            frame = tables[name].copy()
            if not frame.empty:
                frame = frame.sort_index(axis=0)
                frame = frame.sort_index(axis=1)
            path = artifacts.tables_dir / f"{name}.csv"
            frame.to_csv(path, index=True)
            table_links.append((name, path.relative_to(artifacts.output_dir).as_posix()))

        ordered_kpis = {key: kpis[key] for key in sorted(kpis)}
        artifacts.kpi_path.write_text(
            json.dumps(ordered_kpis, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        metadata_payload = dict(metadata)
        metadata_payload["case"] = case_name
        metadata_payload["formulation"] = formulation_name
        artifacts.metadata_path.write_text(
            json.dumps(metadata_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        chart_links: list[tuple[str, str]] = []
        if charts:
            for name in sorted(charts):
                chart_links.append((name, Path(charts[name]).relative_to(artifacts.output_dir).as_posix()))

        artifacts.index_path.write_text(
            self._build_index_html(case_name, formulation_name, ordered_kpis, table_links, chart_links),
            encoding="utf-8",
        )

        return artifacts

    def _build_index_html(
        self,
        case_name: str,
        formulation_name: str,
        kpis: Mapping[str, Any],
        table_links: list[tuple[str, str]],
        chart_links: list[tuple[str, str]],
    ) -> str:
        kpi_rows = "".join(
            f"<tr><th>{key}</th><td>{value}</td></tr>" for key, value in kpis.items()
        )
        table_items = "".join(
            f'<li><a href="{href}">{name}</a></li>' for name, href in table_links
        )
        chart_items = "".join(
            f'<li><a href="{href}">{name}</a></li>' for name, href in chart_links
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{case_name} - {formulation_name}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 0.5rem; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.4rem 0.6rem; text-align: left; }}
    ul {{ line-height: 1.7; }}
  </style>
</head>
<body>
  <h1>{case_name} / {formulation_name}</h1>
  <h2>KPI Snapshot</h2>
  <table>{kpi_rows}</table>
  <h2>Tables</h2>
  <ul>{table_items}</ul>
  <h2>Charts</h2>
  <ul>{chart_items}</ul>
</body>
</html>
"""

