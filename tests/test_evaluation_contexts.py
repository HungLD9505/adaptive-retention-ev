"""Density contexts use allowed prefix counts, never future scores or Final rows."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ev_evaluation.contexts import fit_density_context, validate_analysis_extensions
from ev_models.checkpoint import digest
from tools.development_contexts import authenticate_contexts, fit


class DensityContextTests(unittest.TestCase):
    def test_analysis_extension_identities_cannot_silently_change(self):
        profile = json.loads(Path("configs/issue23/analysis-profile.json").read_text())
        validate_analysis_extensions(profile)
        for key in ("online_phase_days", "load_density_policy", "proxy_relationship_policy"):
            changed = copy.deepcopy(profile)
            changed[key] = "unsupported"
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_analysis_extensions(changed)

    def row(self, entity: str, valid: int, zero: int) -> dict:
        identity = ["fixture", "CITY", entity]
        start, end = "2026-01-01T00:00:00", "2026-01-08T00:00:00"
        return {
            "role": "development",
            "status": "ready",
            "identity": identity,
            "history_days": 7,
            "fit_start": start,
            "cutoff": end,
            "scale": {
                "identity": identity,
                "start": start,
                "cutoff": end,
                "valid_count": valid,
                "zero_count": zero,
            },
        }

    def fit(self, rows: list[dict]) -> dict:
        return fit_density_context(rows, ("fixture", "CITY"), 7, "2026-01-08T00:00:00")

    def test_station_median_ties_missing_and_final_exclusion(self):
        rows = [self.row("a", 10, 10), self.row("b", 100, 50), self.row("c", 1, 0)]
        rows += [self.row("unknown", 0, 0), {"role": "final", "status": "ready"}]
        result = self.fit(rows)
        self.assertEqual(result["threshold"], 0.5)
        self.assertEqual(result["sparse_entities"], 1)
        self.assertEqual(result["dense_entities"], 2)
        self.assertEqual(result["at_threshold_entities"], 1)
        self.assertEqual(result["undefined_entities"], ["unknown"])
        self.assertEqual(result["entities"]["c"]["valid_hours"], 1)
        self.assertNotIn("unknown", result["entities"])
        changed = copy.deepcopy(rows)
        changed[0]["future_score"] = -1e99
        self.assertEqual(self.fit(changed), result)

    def test_zero_activity_is_retained_and_empty_population_undefined(self):
        result = self.fit([self.row("zero", 168, 168)])
        self.assertEqual(result["threshold"], 0)
        self.assertEqual(result["entities"]["zero"]["group"], "dense")
        self.assertIsNone(self.fit([])["threshold"])

    def test_mismatched_prefix_duplicate_or_invalid_counts_fail(self):
        for change in ("identity", "cutoff", "start", "budget", "count", "boolean", "duplicate"):
            with self.subTest(change=change):
                row = self.row("a", 168, 0)
                if change == "identity":
                    row["scale"]["identity"] = ["other", "CITY", "a"]
                elif change == "cutoff":
                    row["cutoff"] = "2026-01-09T00:00:00"
                elif change == "start":
                    row["scale"]["start"] = "2026-01-02T00:00:00"
                elif change == "budget":
                    row["history_days"] = 28
                elif change == "count":
                    row["scale"]["zero_count"] = 169
                elif change == "boolean":
                    row["scale"]["valid_count"] = True
                with self.assertRaises(ValueError):
                    self.fit([row, copy.deepcopy(row)] if change == "duplicate" else [row])

    def test_context_file_is_bound_to_recomputed_metadata_not_an_edited_threshold(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("tools.development_contexts.runtime_code", return_value={"dirty": False}),
        ):
            root = Path(tmp)
            run = root / "fixture-CITY-7d"
            run.mkdir()
            entities = run / "entities.jsonl"
            entities.write_text(json.dumps(self.row("a", 168, 0)) + "\n")
            manifest = {
                "schema": "ev-loader-run-v2",
                "status": "technical_success",
                "config": {
                    "dataset_id": "fixture",
                    "city_id": "CITY",
                    "history_days": 7,
                    "deployment": "2026-01-08T00:00:00",
                },
                "files": {
                    "entities.jsonl": {
                        "sha256": digest(entities),
                        "size_bytes": entities.stat().st_size,
                    }
                },
            }
            (run / "manifest.json").write_text(json.dumps(manifest))
            result = fit(root)
            path = root / "contexts.json"
            path.write_text(json.dumps(result))
            groups = authenticate_contexts(path, digest(path), root)
            self.assertEqual(groups["fixture", "CITY", 7]["threshold"], 1)
            result["groups"][0]["threshold"] = 0.5
            path.write_text(json.dumps(result))
            with self.assertRaises(ValueError):
                authenticate_contexts(path, digest(path), root)
            entities.write_text(entities.read_text() + "\n")
            with self.assertRaises(ValueError):
                fit(root)
