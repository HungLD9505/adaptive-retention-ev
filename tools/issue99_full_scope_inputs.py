"""Owner-authorized historical-cohort follow-up; frozen Final gate stays unchanged."""

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest
from ev_runner.final_gate import FinalAccess, FinalInputRun
from ev_runner.replay import Replay


class FollowupInputs(FinalInputRun):
    """Open only the historical cohort listed in the separate owner-authorized lock."""

    def __init__(self, root: Path, group: dict, access: FinalAccess) -> None:
        if access.lock.get("schema") != "issue99-owner-followup-v1":
            raise ValueError("A separate follow-up lock is required")
        authorization = access.lock.get("owner_authorization", {})
        if authorization.get("request") != "thế chạy thử cả như đợt trc đi xem có thắng dc k":
            raise ValueError("Missing explicit owner request for historical-cohort experiment")
        self.prefixes = {}
        super().__init__(root, group["input_manifest_sha256"], access)
        if self.source_hash != group["source_population_sha256"]:
            raise ValueError("Source population mismatch")

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        self.check_target(entity_id)
        if (role, entity_id) not in self.prefixes:
            self.prefixes[(role, entity_id)] = super().training(role, entity_id)
        return self.prefixes[(role, entity_id)]

    def reauthenticate(self) -> None:
        """Rehash all immutable artifacts after the group completes."""
        from ev_models.data import InputRun

        for name in self.manifest["files"]:
            InputRun.verify(self, name)


def historical_vectors(record: dict, replay: Replay) -> dict:
    """Verify old multi-candidate forecasts against labels and their score-event hashes."""
    folder = Path(record["path"])
    if digest(folder / "run.json") != record["report_sha256"]:
        raise ValueError("Historical run report hash differs from collection")
    report = json.loads((folder / "run.json").read_text())
    binding = report["binding"]["input"]
    if (
        binding["input_manifest_sha256"] != replay.inputs.sha256
        or binding["entity_id"] != replay.entity_id
        or binding["history_days"] != replay.inputs.config["history_days"]
    ):
        raise ValueError("Historical run input binding mismatch")
    forecasts = {}
    for path in sorted(folder.glob("tick-*/forecasts.json")):
        forecast = json.loads(path.read_text())
        if forecast:
            if forecast["origin"] in forecasts:
                raise ValueError("Duplicate historical forecast")
            forecasts[forecast["origin"]] = (forecast, digest(path))
    rows = {}
    for path in sorted(folder.glob("tick-*/events.jsonl")):
        for event in map(json.loads, path.read_text().splitlines()):
            if event["event"] != "score":
                continue
            origin = event["origin"]
            if origin in rows:
                raise ValueError("Duplicate historical score")
            forecast, sha = forecasts[origin]
            if sha != event["prediction_sha256"]:
                raise ValueError("Historical forecast checksum differs")
            labels = replay.labels(
                datetime.fromisoformat(origin), datetime.fromisoformat(event["as_of"])
            )
            if labels.status != "complete":
                raise ValueError("Historical score uses unavailable labels")
            vectors = np.asarray(forecast["predictions"]) * replay.scale
            if vectors.shape != (len(report["candidate_levels"]), 24):
                raise ValueError("Historical candidate vector shape differs")
            mae = np.abs(vectors - labels.values).mean(axis=1)
            np.testing.assert_allclose(
                mae, np.asarray(event["mae_scaled"]) * replay.scale, atol=1e-8, rtol=1e-10
            )
            active = report["candidate_levels"].index(event["issued_active"])
            rows[origin] = {
                "as_of": event["as_of"],
                "vectors": vectors.tolist(),
                "mae": mae.tolist(),
                "active_mae": float(mae[active]),
                "sha256": sha,
                "prediction_ids": forecast["prediction_ids"],
            }
    if len(rows) != report["scored_days"]:
        raise ValueError("Historical score coverage mismatch")
    mean = sum(r["active_mae"] for r in rows.values()) / len(rows) if rows else None
    if mean is None:
        if report["active_mae_kwh"] is not None:
            raise ValueError("Historical null score mismatch")
    elif not math.isclose(mean, report["active_mae_kwh"], abs_tol=1e-8, rel_tol=1e-10):
        raise ValueError("Historical active MAE mismatch")
    return {"rows": rows, "levels": report["candidate_levels"], "mae": mean}
