"""Smoke tests for gas dispatch case solving and artifact generation.

This module contains end-to-end integration tests for the optimization pipeline:
  - Verifies that a small case can be loaded and solved successfully
  - Confirms that all expected output artifacts are created
  - Serves as a quick validation that the entire pipeline works

Tests:
  - SmokeSolveTests.test_custom_case_writes_artifacts:
      Runs the custom 4-node case with quadratic formulation and verifies:
      1. Optimization completes with OPTIMAL status
      2. Output directory structure is created
      3. Required HTML index, KPI JSON, and CSV tables are written

Note: These tests use an isolated test_outputs directory and clean up after themselves.

Run tests:
    python -m pytest tests/test_smoke_solve.py -v
    python -m unittest tests.test_smoke_solve -v
"""

from __future__ import annotations

import shutil
from pathlib import Path
import unittest

from src.common.context import RunConfig
from src.common.runner import run_case


class SmokeSolveTests(unittest.TestCase):
    """End-to-end integration tests for case solving and artifact generation."""

    def test_custom_case_writes_artifacts(self) -> None:
        """Test that custom 4-node case solves and produces all output artifacts.
        
        Validates the entire pipeline:
          1. Load custom_MP_4nodes case from data/
          2. Solve with weymouth_ogd (quadratic) formulation
          3. Verify optimal solution found
          4. Confirm all required output files are created:
             - index.html (report)
             - kpi_snapshot.json (key performance indicators)
             - node_pressure.csv (solution table)
        
        Uses isolated test_outputs directory; automatically cleaned up after test.
        """
        output_root = Path.cwd() / "test_outputs"
        
        # Clean up any previous test artifacts
        if output_root.exists():
            shutil.rmtree(output_root)
        
        try:
            # Configure and run the case
            config = RunConfig(
                case="custom_MP_4nodes",
                formulation="weymouth_ogd",
                data_roots=(Path("data"),),
                output_root=output_root,
            )
            outcome = run_case(config)

            # Verify solution status
            self.assertEqual(
                outcome.result.status, "OPTIMAL",
                "Case should solve to optimality"
            )
            
            # Verify output directory exists
            self.assertTrue(
                outcome.output_dir.exists(),
                f"Output directory should exist at {outcome.output_dir}"
            )
            
            # Verify required report file
            self.assertTrue(
                (outcome.output_dir / "index.html").exists(),
                "HTML report (index.html) should be generated"
            )
            
            # Verify KPI metadata
            self.assertTrue(
                (outcome.output_dir / "kpi_snapshot.json").exists(),
                "KPI snapshot (kpi_snapshot.json) should be generated"
            )
            
            # Verify solution table
            self.assertTrue(
                (outcome.output_dir / "tables" / "node_pressure.csv").exists(),
                "Node pressure table should be written to tables/node_pressure.csv"
            )
            
        finally:
            # Always clean up test artifacts
            if output_root.exists():
                shutil.rmtree(output_root)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
