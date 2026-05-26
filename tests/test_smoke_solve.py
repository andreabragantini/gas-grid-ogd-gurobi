"""Smoke test for the incremental Weymouth run path."""

from __future__ import annotations

import shutil
from pathlib import Path
import unittest

from src.common.context import RunConfig
from src.common.runner import run_case


class SmokeSolveTests(unittest.TestCase):
    def test_custom_case_writes_artifacts(self) -> None:
        output_root = Path.cwd() / "test_outputs"
        if output_root.exists():
            shutil.rmtree(output_root)
        try:
            config = RunConfig(
                case="custom_MP_4nodes",
                formulation="weymouth_ogd",
                data_roots=(Path("data"),),
                output_root=output_root,
            )
            outcome = run_case(config)

            self.assertEqual(outcome.result.status, "OPTIMAL")
            self.assertTrue(outcome.output_dir.exists())
            self.assertTrue((outcome.output_dir / "index.html").exists())
            self.assertTrue((outcome.output_dir / "kpi_snapshot.json").exists())
            self.assertTrue((outcome.output_dir / "tables" / "node_pressure.csv").exists())
        finally:
            if output_root.exists():
                shutil.rmtree(output_root)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
