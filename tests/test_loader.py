"""Tests for schema harmonization and validation."""

from __future__ import annotations

import shutil
from pathlib import Path
import unittest

import pandas as pd

from src.common.loader import load_case
from src.common.validation import ValidationError


class LoaderTests(unittest.TestCase):
    def test_alias_resolution_and_unit_normalization(self) -> None:
        root = self._prepare_root("loader_alias")
        try:
            case_dir = root / "toy_case"
            case_dir.mkdir(parents=True)

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

            data = load_case("toy_case", data_roots=(root,))

            self.assertListEqual(sorted(data.nodes["uid"].tolist()), ["n1", "n2"])
            self.assertAlmostEqual(float(data.pipes.loc[0, "length_km"]), 1.0)
            self.assertAlmostEqual(float(data.pipes.loc[0, "diameter_mm"]), 150.0)
            self.assertAlmostEqual(float(data.nodes.loc[0, "p_min_kpa"]), 2.0)
            self.assertAlmostEqual(float(data.nodes.loc[0, "p_max_kpa"]), 6.0)
            self.assertEqual(data.suppliers.loc[0, "node_id"], "n1")
            self.assertEqual(data.metadata["input_files"], ["gas_nodes.csv", "gas_pipes.csv", "gas_reservoir.csv"])
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_missing_required_node_reference_fails(self) -> None:
        root = self._prepare_root("loader_invalid")
        try:
            case_dir = root / "broken_case"
            case_dir.mkdir(parents=True)

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

            with self.assertRaises(ValidationError):
                load_case("broken_case", data_roots=(root,))
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_optional_load_file_is_allowed(self) -> None:
        root = self._prepare_root("loader_optional")
        try:
            case_dir = root / "optional_case"
            case_dir.mkdir(parents=True)

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

            data = load_case("optional_case", data_roots=(root,))
            self.assertTrue(data.loads.empty)
        finally:
            if root.exists():
                shutil.rmtree(root)

    def _prepare_root(self, suffix: str) -> Path:
        root = Path.cwd() / f"tmp_{suffix}"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        return root


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
