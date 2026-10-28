"""Offline guards for outcome-blind Final metadata extraction."""

from __future__ import annotations

import json
import unittest

from tools.hung_final_metadata_preflight import final_ids, rank_entity


class _MetadataOnlyArchive:
    def __init__(self, entities: list[dict]) -> None:
        prefix = "data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-7d/"
        manifest = {
            "config": {"history_days": 7, "dataset_id": "urbanev", "city_id": "SZH"},
            "counts": {"final": sum(row["role"] == "final" for row in entities)},
        }
        self.members = {
            prefix + "manifest.json": json.dumps(manifest).encode(),
            prefix + "entities.jsonl": b"\n".join(json.dumps(row).encode() for row in entities),
        }
        self.read_names: list[str] = []

    def read(self, name: str) -> bytes:
        self.read_names.append(name)
        return self.members[name]


def _entity(entity_id: str, role: str = "final") -> dict:
    return {
        "identity": ["urbanev", "SZH", entity_id],
        "role": role,
        "history_days": 7,
        "coverage": {"should_not_be_used_for_selection": 0},
    }


class FinalMetadataTests(unittest.TestCase):
    def test_reads_only_manifest_and_entity_metadata(self) -> None:
        archive = _MetadataOnlyArchive([_entity("1003"), _entity("1004", "development")])
        identities, manifest_hash = final_ids(archive, 7)
        self.assertEqual(identities, {"1003"})
        self.assertEqual(len(manifest_hash), 64)
        self.assertEqual(len(archive.read_names), 2)
        self.assertTrue(
            all(name.endswith(("manifest.json", "entities.jsonl")) for name in archive.read_names)
        )

    def test_duplicate_final_identity_rejected(self) -> None:
        archive = _MetadataOnlyArchive([_entity("1003"), _entity("1003")])
        with self.assertRaisesRegex(ValueError, "Duplicate Final entity"):
            final_ids(archive, 7)

    def test_rank_uses_id_without_outcome_fields(self) -> None:
        self.assertEqual(rank_entity("1003"), rank_entity("1003"))
        self.assertNotEqual(rank_entity("1003"), rank_entity("1004"))


if __name__ == "__main__":
    unittest.main()
