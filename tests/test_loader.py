"""Tests for data loading, schema harmonization, and validation.

This module validates the core data loading pipeline that is critical for
ensuring consistent data handling across different case formats:

  - Alias resolution: Different CSV headers map to canonical column names
  - Unit normalization: Length (m/km), diameter (m/mm), pressure (Pa/bar/MPa)
  - Validation: Required fields are present and reference integrity is maintained
  - Optional files: Missing non-critical files don't break loading

Tests:
  - LoaderTests.test_alias_resolution_and_unit_normalization:
      Verifies that a case with mixed header names and mixed units correctly
      normalizes to canonical schema.
  
  - LoaderTests.test_missing_required_node_reference_fails:
      Ensures validation catches broken node references (pipe references node
      that doesn't exist).
  
  - LoaderTests.test_optional_load_file_is_allowed:
      Confirms that optional files (like gas_loads_special.csv) can be omitted
      without errors.

Run tests:
    python -m pytest tests/test_loader.py -v
    python -m unittest tests.test_loader -v
"""

from __future__ import annotations

import shutil
from pathlib import Path
import unittest

import pandas as pd

from src.common.loader import load_case
from src.common.validation import ValidationError


class LoaderTests(unittest.TestCase):
    """Tests for data loading, schema harmonization, and validation."""

    def test_alias_resolution_and_unit_normalization(self) -> None:
        """Test that legacy column names and mixed units are harmonized to canonical form.
        
        This test validates the schema aliasing system which allows different
        datasets with different CSV headers to be loaded into a canonical schema:
        
        Input variations handled:
          - Column names: UID/ID, PRmin/p_min, Qdemand/demand
          - Delimiters: semicolon (;) in nodes, comma (,) in pipes
          - Units: length_m → length_km, diameter_m → diameter_mm, pressure values as-is
        
        Expected output:
          - All columns normalized to lowercase canonical names
          - All units converted to canonical units (km, mm, kPa)
          - Metadata records which input files were processed
        """
        root = self._prepare_root("loader_alias")
        try:
            case_dir = root / "toy_case"
            case_dir.mkdir(parents=True)

            # Create test data with mixed headers and delimiters
            (case_dir / "gas_nodes.csv").write_text(
                "UID;PRmin;PRmax;Qdemand;gix_x;gix_y\n"
                "n1;2;6;0;1;2\n"
                "n2;2;6;1;3;4\n",
                encoding="utf-8",
            )
            (case_dir / "gas_pipes.csv").write_text(
                "UID,fromNode,toNode,length_m,diameter_m,Friction\n"
                "p1,n1,n2,1000,0.15,0.01\n",
                encoding="utf-8",
            )
            (case_dir / "gas_reservoir.csv").write_text(
                "ID,Origin,Capacity,Cost\n"
                "s1,n1,10,20\n",
                encoding="utf-8",
            )

            # Load and verify
            data = load_case("toy_case", data_roots=(root,))

            # Verify node UIDs are lowercase
            self.assertListEqual(sorted(data.nodes["uid"].tolist()), ["n1", "n2"])
            
            # Verify unit conversions: 1000m → 1.0km
            self.assertAlmostEqual(float(data.pipes.loc[0, "length_km"]), 1.0)
            
            # Verify unit conversions: 0.15m → 150mm
            self.assertAlmostEqual(float(data.pipes.loc[0, "diameter_mm"]), 150.0)
            
            # Verify pressure normalization (already in kPa)
            self.assertAlmostEqual(float(data.nodes.loc[0, "p_min_kpa"]), 2.0)
            self.assertAlmostEqual(float(data.nodes.loc[0, "p_max_kpa"]), 6.0)
            
            # Verify supplier reference
            self.assertEqual(data.suppliers.loc[0, "node_id"], "n1")
            
            # Verify metadata tracking
            self.assertEqual(
                data.metadata["input_files"],
                ["gas_nodes.csv", "gas_pipes.csv", "gas_reservoir.csv"]
            )
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_missing_required_node_reference_fails(self) -> None:
        """Test that validation catches broken node references.
        
        Validates that the data loader detects reference integrity violations:
        A pipe references node n2, but only n1 is defined in the nodes table.
        
        Expected behavior:
          - ValidationError should be raised during loading
          - Error message should indicate the broken reference
        """
        root = self._prepare_root("loader_invalid")
        try:
            case_dir = root / "broken_case"
            case_dir.mkdir(parents=True)

            # Create data with undefined node reference
            (case_dir / "gas_nodes.csv").write_text(
                "UID,PRmin,PRmax,Qdemand\n"
                "n1,1,5,0\n",
                encoding="utf-8",
            )
            (case_dir / "gas_pipes.csv").write_text(
                "UID,fromNode,toNode,Length,Diameter\n"
                "p1,n1,n2,1,100\n",
                encoding="utf-8",
            )
            (case_dir / "gas_reservoir.csv").write_text(
                "ID,Origin,Capacity,Cost\n"
                "s1,n1,10,20\n",
                encoding="utf-8",
            )

            # Verify that validation fails
            with self.assertRaises(ValidationError):
                load_case("broken_case", data_roots=(root,))
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_optional_load_file_is_allowed(self) -> None:
        """Test that optional files (like gas_loads_special.csv) can be omitted.
        
        Validates that the loader gracefully handles missing optional files.
        Only required files (nodes, pipes, suppliers) must be present.
        
        Expected behavior:
          - Loading succeeds without gas_loads_special.csv
          - data.loads should be an empty DataFrame (not None)
          - No error or warning is raised
        """
        root = self._prepare_root("loader_optional")
        try:
            case_dir = root / "optional_case"
            case_dir.mkdir(parents=True)

            # Create only required files (no gas_loads_special.csv)
            (case_dir / "gas_nodes.csv").write_text(
                "UID,PRmin,PRmax,Qdemand\n"
                "n1,1,5,0\n"
                "n2,1,5,1\n",
                encoding="utf-8",
            )
            (case_dir / "gas_pipes.csv").write_text(
                "UID,fromNode,toNode,Length,Diameter\n"
                "p1,n1,n2,1,100\n",
                encoding="utf-8",
            )
            (case_dir / "gas_reservoir.csv").write_text(
                "ID,Origin,Capacity,Cost\n"
                "s1,n1,10,20\n",
                encoding="utf-8",
            )

            # Load and verify optional file absence
            data = load_case("optional_case", data_roots=(root,))
            self.assertTrue(
                data.loads.empty,
                "Optional loads file is missing; loads DataFrame should be empty"
            )
        finally:
            if root.exists():
                shutil.rmtree(root)

    def _prepare_root(self, suffix: str) -> Path:
        """Create an isolated temporary directory for test data.
        
        Args:
            suffix: String to suffix the temporary directory name with.
        
        Returns:
            Path object pointing to the created temporary directory.
        """
        root = Path.cwd() / f"tmp_{suffix}"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        return root


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
