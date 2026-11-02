"""Read #18 artifacts; ordinary inputs remain Development-only for target values."""

import hashlib
import json
import math
from dataclasses import fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from ev_inputs.features import SCHEMA_ID, calendar_features
from ev_inputs.loader import MISSING_DATA_POLICY, SUCCESS_STATUSES
from ev_inputs.splits import entity_role
from ev_inputs.windows import ForecastInput
from ev_models.checkpoint import digest

DAY = timedelta(days=1)
HOUR = timedelta(hours=1)


def jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


class InputRun:
    """Validate manifest, artifacts, identities, prefix containment and normalized labels."""

    target_role = "development"

    def check_target(self, entity_id: str) -> None:
        """Check scope before selected target values are decoded."""
        summary = self.entities.get((*self.namespace, entity_id), {})
        if summary.get("role") != self.target_role or summary.get("status") != "ready":
            raise ValueError("Only ready declared Development/approved Final targets permitted")

    def __init__(self, root: Path, sha256: str) -> None:
        self.root = root
        self.sha256 = sha256
        if digest(root / "manifest.json") != sha256:
            raise ValueError("Input manifest SHA-256 mismatch")
        self.manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        m = self.manifest
        if (
            m.get("schema") != "ev-loader-run-v2"
            or m.get("feature_schema") != SCHEMA_ID
            or m.get("missing_data_policy") != MISSING_DATA_POLICY
            or m.get("status") not in SUCCESS_STATUSES
        ):
            raise ValueError("Only identified successful accepted-policy input runs are supported")
        self.config = m["config"]
        self.deployment = datetime.fromisoformat(self.config["deployment"])
        self.clock = m["source"]["clock_mode"]
        self.namespace = (self.config["dataset_id"], self.config["city_id"])
        if self.config["history_days"] not in (7, 14, 28):
            raise ValueError("Unsupported history budget")
        for name in ("entities.jsonl", "training.jsonl"):
            self.verify(name)
        self.entities = {}
        for record in jsonl(root / "entities.jsonl"):
            identity = tuple(record["identity"])
            if identity in self.entities or identity[:2] != self.namespace:
                raise ValueError("Duplicate/wrong-namespace entity")
            if record["role"] != entity_role(*identity, salt=self.config["split_salt"]):
                raise ValueError("Entity split differs from declared salt")
            if datetime.fromisoformat(record["cutoff"]) != self.deployment:
                raise ValueError("Entity cutoff mismatch")
            self.entities[identity] = record
        self.source_hash = self._source_identity()

    def verify(self, name: str) -> None:
        if name not in {
            "training.jsonl",
            "entities.jsonl",
            "forecasts.jsonl",
            "labels.jsonl",
            "schedule.jsonl",
        }:
            raise ValueError("Unsupported artifact name")
        expected = self.manifest["files"][name]
        path = self.root / name
        if path.stat().st_size != expected["size_bytes"] or digest(path) != expected["sha256"]:
            raise ValueError(f"Input artifact mismatch: {name}")

    def _source_identity(self) -> str:
        payload = {
            "namespace": self.namespace,
            "source_start": self.config["source_start"],
            "deployment": self.config["deployment"],
            "salt": self.config["split_salt"],
            "clock": self.clock,
            "availability_delay_hours": self.config["availability_delay_hours"],
            "hourly_sha256": self.manifest["source"]["hourly_sha256"],
            "policy": self.manifest["missing_data_policy"],
            "entities": [r for _, r in sorted(self.entities.items()) if r["role"] == "source"],
        }
        # Source entity summaries have no budget-dependent fields in #18 outputs.
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def validate_forecast(self, record: dict, *, role: str, before_deployment: bool) -> dict:
        identity = tuple(record["identity"])
        summary = self.entities.get(identity)
        if summary is None or summary["role"] != role or record.get("role") != role:
            raise ValueError("Wrong entity/role")
        if (
            record["schema_id"] != SCHEMA_ID
            or record["input_run_id"] != self.manifest["run_id"]
            or record["clock_mode"] != self.clock
            or summary["status"] != "ready"
        ):
            raise ValueError("Forecast schema/run/profile mismatch")
        scale = summary["scale"]
        if (
            record["scale_id"] != scale["fit_sha256"]
            or record["energy_scale"] != scale["energy_scale"]
        ):
            raise ValueError("Scaler binding mismatch")
        origin = datetime.fromisoformat(record["origin"])
        if origin.utcoffset() != self.deployment.utcoffset() or any(
            (origin.hour, origin.minute, origin.second, origin.microsecond)
        ):
            raise ValueError("Origin must use declared local midnight")
        if record["history_labels"] != [(origin - (24 - i) * HOUR).isoformat() for i in range(24)]:
            raise ValueError("History is not consecutive 24 bins")
        if record["future_labels"] != [(origin + i * HOUR).isoformat() for i in range(24)]:
            raise ValueError("Horizon is not consecutive 24 bins")
        start = (
            datetime.fromisoformat(self.config["source_start"])
            if role == "source"
            else self.deployment - self.config["history_days"] * DAY
        )
        if datetime.fromisoformat(summary["fit_start"]) != start:
            raise ValueError("Entity prefix start mismatch")
        if before_deployment:
            if origin - DAY < start or origin + DAY > self.deployment:
                raise ValueError("Initial X/Y outside allowed prefix")
        elif not self.deployment <= origin < datetime.fromisoformat(self.config["replay_stop"]):
            raise ValueError("Forecast outside replay bounds")
        x, c = record["x_hist"], record["c_future"]
        if len(x) != 24 or len(c) != 24:
            raise ValueError("Expected 24 rows")
        for i, row in enumerate(x):
            if len(row) != 7 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in row
            ):
                raise ValueError("Invalid historical features")
            if row[-1] not in (0, 1) or row[0] < 0 or (row[-1] == 0 and row[0] != 0):
                raise ValueError("Invalid missing/zero semantics")
            expected = calendar_features(origin - (24 - i) * HOUR, clock_mode=self.clock)
            if any(
                not math.isclose(a, b, abs_tol=2e-7)
                for a, b in zip(row[1:6], expected, strict=True)
            ):
                raise ValueError("Historical calendar mismatch")
        if not any(row[-1] for row in x):
            raise ValueError("All-missing history must be skipped")
        for i, row in enumerate(c):
            expected = calendar_features(origin + i * HOUR, clock_mode=self.clock)
            if len(row) != 5 or any(
                not math.isfinite(a) or not math.isclose(a, b, abs_tol=2e-7)
                for a, b in zip(row, expected, strict=True)
            ):
                raise ValueError("Future calendar mismatch")
        return {**record, "entity_id": identity[2]}

    def _selected_rows(self, name: str, role: str, entity_id: str | None) -> Iterator[dict]:
        """Authenticate all bytes, decode only the requested publisher-profile header.

        The accepted #18 writer places role and identity before value arrays. This
        narrow adapter deliberately rejects another serialization profile rather
        than falling back to decoding unselected records.
        """
        self.verify(name)
        nested = '"forecast": {' if name == "training.jsonl" else ""
        headers = {
            r: ('{"role": "' + r + '", ' + nested + '"identity": ').encode()
            for r in ("source", "development", "final")
        }
        prefix = headers[role]
        if entity_id is not None:
            prefix += json.dumps([*self.namespace, entity_id], ensure_ascii=False).encode() + b","
        with (self.root / name).open("rb") as stream:
            for line in stream:
                if not any(line.startswith(header) for header in headers.values()):
                    raise ValueError(f"Unsupported identified-row serialization: {name}")
                if line.startswith(prefix):
                    yield json.loads(line)

    def replay_forecasts(self, entity_id: str) -> Iterator[dict]:
        """Yield only one permitted ready target; other entity values stay opaque."""
        self.check_target(entity_id)
        expected = {field.name for field in fields(ForecastInput)} | {"role"}
        for record in self._selected_rows("forecasts.jsonl", self.target_role, entity_id):
            if set(record) != expected:
                raise ValueError("Predictor record contains unexpected/missing fields")
            yield record

    def evaluation_labels(self, entity_id: str, origins: set[str]) -> Iterator[dict]:
        """Static evaluator: decode Y only for this permitted target's issued days."""
        self.check_target(entity_id)
        self.verify("labels.jsonl")
        prefix = (
            '{"identity": '
            + json.dumps([*self.namespace, entity_id], ensure_ascii=False)
            + ', "origin": "'
        ).encode()
        with (self.root / "labels.jsonl").open("rb") as stream:
            for line in stream:
                if not line.startswith(b'{"identity": '):
                    raise ValueError("Unsupported identified label serialization")
                if not line.startswith(prefix):
                    continue
                stamp = line[len(prefix) :].split(b'"', 1)[0].decode()
                if stamp in origins:
                    yield json.loads(line)

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        if role not in ("source", self.target_role) or (
            role == self.target_role and entity_id is None
        ):
            raise ValueError(
                "Training permits source or one explicitly identified Development target"
            )
        if role == self.target_role:
            self.check_target(entity_id)
        if (
            entity_id is not None
            and self.entities.get((*self.namespace, entity_id), {}).get("role") != role
        ):
            raise ValueError("Requested target is absent or not Development")
        result = []
        seen = set()
        for rec in self._selected_rows("training.jsonl", role, entity_id):
            # Validate the selected header again after decoding the selected body.
            if rec["role"] != role or (
                entity_id is not None and rec["forecast"]["identity"][2] != entity_id
            ):
                raise ValueError("Selected training header disagrees with decoded identity")
            forecast = self.validate_forecast(
                {**rec["forecast"], "role": role}, role=role, before_deployment=True
            )
            key = (forecast["entity_id"], forecast["origin"])
            if key in seen:
                raise ValueError("Duplicate training sample")
            seen.add(key)
            y, scaled = rec["y_kwh"], rec["y_scaled"]
            if len(y) != 24 or len(scaled) != 24:
                raise ValueError("Incomplete labels")
            for a, b in zip(y, scaled, strict=True):
                if (
                    a is None
                    or b is None
                    or not math.isfinite(a)
                    or not math.isfinite(b)
                    or a < 0
                    or not math.isclose(a / forecast["energy_scale"], b, rel_tol=2e-6, abs_tol=2e-7)
                ):
                    raise ValueError("Invalid/inconsistent normalized labels")
            result.append({**forecast, "y_kwh": y, "y_scaled": scaled})
        expected_count = (
            self.entities[(*self.namespace, entity_id)]["initial_trainable"]
            if entity_id is not None
            else sum(
                row["initial_trainable"] for row in self.entities.values() if row["role"] == role
            )
        )
        if len(result) != expected_count:
            raise ValueError("Selected training population differs from identified summary")
        return result

    def binding(
        self, stage: str, entity_id: str | None = None, source_checkpoint_sha256: str | None = None
    ) -> dict:
        summary = self.entities[(*self.namespace, entity_id)] if entity_id else None
        return {
            "schema": "ev-checkpoint-input-binding-v1",
            "feature_schema": SCHEMA_ID,
            "input_manifest_sha256": self.sha256,
            "input_run_id": self.manifest["run_id"],
            "dataset_id": self.namespace[0],
            "city_id": self.namespace[1],
            "stage": stage,
            "entity_id": entity_id,
            "history_days": self.config["history_days"] if summary else None,
            "scale_id": summary["scale"]["fit_sha256"] if summary else None,
            "source_checkpoint_sha256": source_checkpoint_sha256,
        }
