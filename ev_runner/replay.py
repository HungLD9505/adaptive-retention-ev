"""Identified Development inputs and separately gated labels for daily replay."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from ev_inputs.loader import iter_forecasts
from ev_inputs.windows import LabelRecord, ready_labels
from ev_models.data import InputRun, jsonl

DAY = timedelta(days=1)


@dataclass(frozen=True)
class Labels:
    status: str
    values: tuple[float, ...] | None
    available_at: datetime | None


class Replay:
    """Predictor gets only current X/calendar; labels are a separate delayed provider."""

    def __init__(self, inputs: InputRun, entity_id: str, days: int) -> None:
        self.inputs = inputs
        self.entity_id = entity_id
        self.start = inputs.deployment
        self.stop = self.start + days * DAY
        self.identity = (*inputs.namespace, entity_id)
        summary = inputs.entities.get(self.identity, {})
        if summary.get("role") != "development" or summary.get("status") != "ready":
            raise ValueError("Only ready Development targets may enter this smoke runner")
        if days < 1 or self.stop > datetime.fromisoformat(inputs.config["replay_stop"]):
            raise ValueError("Invalid replay horizon")
        self.scale_id = summary["scale"]["fit_sha256"]
        self.scale = summary["scale"]["energy_scale"]
        self.delay = timedelta(hours=inputs.config["availability_delay_hours"])
        self.forecasts = {}
        for r in iter_forecasts(inputs.root, expected_manifest_sha256=inputs.sha256):
            if tuple(r["identity"]) != self.identity:
                continue
            origin = datetime.fromisoformat(r["origin"])
            if self.start <= origin < self.stop:
                if origin in self.forecasts:
                    raise ValueError("Duplicate replay forecast")
                self.forecasts[origin] = inputs.validate_forecast(
                    r, role="development", before_deployment=False
                )
        inputs.verify("schedule.jsonl")
        self.schedule = {}
        self._label_offsets = None
        for r in jsonl(inputs.root / "schedule.jsonl"):
            if tuple(r["identity"]) == self.identity:
                origin = datetime.fromisoformat(r["origin"])
                if self.start <= origin < self.stop:
                    if origin in self.schedule:
                        raise ValueError("Duplicate scheduled origin")
                    self.schedule[origin] = r["status"]
        if len(self.schedule) != days or any(
            (status == "created") != (origin in self.forecasts)
            for origin, status in self.schedule.items()
        ):
            raise ValueError("Forecasts do not account for every scheduled day")
        # Hashing bytes authenticates the artifact; it does not expose label values to predictor.
        inputs.verify("labels.jsonl")

    def forecast(self, origin: datetime) -> dict | None:
        return self.forecasts.get(origin)

    def labels(self, origin: datetime, as_of: datetime) -> Labels:
        """Decode only the requested day, after its scheduled availability lower bound."""
        if as_of < origin + DAY + self.delay:
            return Labels("pending", None, origin + DAY + self.delay)
        # Match identified writer fields before decoding energy arrays. This narrow
        # adapter consumes the authenticated #18 JSONL representation, not arbitrary JSON.
        path = self.inputs.root / "labels.jsonl"
        if self._label_offsets is None:
            self._label_offsets = {}
            prefix = ('{"identity": ' + json.dumps(list(self.identity)) + ', "origin": "').encode()
            # Index only public row identity/time headers; future energy arrays remain opaque.
            with path.open("rb") as stream:
                while True:
                    offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    if line.startswith(prefix):
                        stamp = line[len(prefix) :].split(b'"', 1)[0].decode()
                        if stamp in self._label_offsets:
                            raise ValueError("Duplicate target label day")
                        self._label_offsets[stamp] = offset
        if origin.isoformat() not in self._label_offsets:
            raise ValueError("Expected one identified label record per scheduled origin")
        with path.open("rb") as stream:
            stream.seek(self._label_offsets[origin.isoformat()])
            r = json.loads(stream.readline())
        if tuple(r["identity"]) != self.identity or r["origin"] != origin.isoformat():
            raise ValueError("Indexed label identity/time differs")
        label = LabelRecord(
            self.identity,
            origin,
            r["clock_mode"],
            tuple(datetime.fromisoformat(x) for x in r["timestamps"]),
            tuple(r["energy_kwh"]),
            tuple(r["file_valid"]),
            tuple(datetime.fromisoformat(x) if x else None for x in r["available_at"]),
        )
        if label.clock_mode != self.inputs.clock:
            raise ValueError("Label clock differs from predictor")
        arrivals = [x for x in label.available_at if x is not None]
        complete = all(label.file_valid) and all(x is not None for x in label.available_at)
        if not complete:
            return Labels("incomplete", None, as_of)
        latest = max(origin + DAY, max(arrivals))
        if latest > as_of:
            return Labels("pending", None, latest)
        values = ready_labels(label, as_of=as_of)
        if values is None:
            raise ValueError("Complete arrived label record failed the label gate")
        return Labels("complete", values, latest)
