"""Publish verified completed runs to mounted storage; never change training policy."""

import json
import os
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

import torch

from ev_models.checkpoint import digest, load_checkpoint
from tools.export_development import put_file, put_run, safe_name
from tools.verify_comparison import InputSnapshots, verify_run
from tools.verify_latest_states import verify_state


def require_drive_mount(backup: Path, mount: Path) -> None:
    """Reject an ordinary local directory masquerading as a mounted Drive backup."""
    resolved, storage = backup.resolve(), mount.resolve(strict=True)
    if not mount.is_mount() or resolved == storage or not resolved.is_relative_to(storage):
        raise ValueError("Backup must be below an existing, explicitly identified Drive mount")


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


class RunBackup:
    """One study, immutable context and one receipt per completed Source/target."""

    def __init__(
        self, study: Path, backup: Path, context: dict, inputs: dict, *, resume: bool = False
    ) -> None:
        self.study, self.root, self.context, self.inputs = study, backup, context, inputs
        if study.resolve().is_relative_to(backup.resolve()) or backup.resolve().is_relative_to(
            study.resolve()
        ):
            raise ValueError("Study and backup directories must be separate")
        self.snapshots = InputSnapshots()
        self.sources: dict[int, dict] = {}
        self.runs: dict[str, dict] = {}
        if resume:
            if (backup / "context.json").read_bytes() != canonical(context):
                raise ValueError("Changed backup code/environment/input/cohort/config context")
            if list(backup.glob("*.pending")):
                raise ValueError(
                    "Interrupted backup publication; preserve and inspect pending bytes"
                )
        else:
            backup.mkdir(parents=True, exist_ok=False)
            with (backup / "context.json").open("xb") as stream:
                stream.write(canonical(context))
                stream.flush()
                os.fsync(stream.fileno())
        self.context_sha = digest(backup / "context.json")

    def check_source(self, entry: dict) -> Path:
        seed = entry["seed"]
        if type(seed) is not int or seed not in self.context["seeds"]:
            raise ValueError("Unexpected Source seed")
        path = self.study / f"source-seed{seed}" / f"epoch-{self.context['source_epochs']}.pt"
        # Reload constructs a CPU model. Verification must not perturb training RNG.
        with torch.random.fork_rng(devices=[]):
            _, _, value = load_checkpoint(path, sha256=entry["sha256"], device="cpu")
        meta, latent = value["metadata"], value["latent_scale"]
        report = json.loads((path.parent / "run.json").read_text())
        if (
            meta["input_binding"]["stage"] != "source"
            or (meta["input_binding"]["dataset_id"], meta["input_binding"]["city_id"])
            != tuple(self.context["namespace"])
            or meta["input_binding"]["input_manifest_sha256"]
            != self.context["source_manifest_sha256"]
            or meta["source_population_sha256"] != self.context["source_population_sha256"]
            or meta["training_config"] != {**self.context["source_training"], "seed": seed}
            or value["completed_epochs"] != self.context["source_epochs"]
            or meta["code"]["dirty"]
            or meta["code"]["files"]
            != {k: v for k, v in self.context["core_files"].items() if k.startswith("ev_models/")}
            or report != entry["run"]
            or report.get("status") != "technical_success"
            or report.get("checkpoint_sha256") != entry["sha256"]
            or any(
                report.get(k) != meta.get(k)
                for k in (
                    "input_binding",
                    "source_population_sha256",
                    "training_config",
                    "code",
                    "environment",
                )
            )
            or path.with_name(path.name + ".sha256").read_text().strip() != entry["sha256"]
            or latent is None
            or latent.shape != (64,)
            or not torch.isfinite(latent).all()
            or (latent < 0).any()
        ):
            raise ValueError("Source metadata/seed/population/latent scale changed")
        return path

    def check_run(self, row: dict) -> tuple[dict, dict]:
        name = safe_name(row["run_id"])
        expected = self.context["expected_runs"].get(name)
        binding, config = row["binding"]["input"], row["binding"]["config"]
        seed = config["initial_training"]["seed"]
        if (
            expected is None
            or set(self.sources) != set(self.context["seeds"])
            or config != expected["config"]
            or row.get("comparison_variant") != expected.get("comparison_variant")
            or binding["entity_id"] != expected["entity_id"]
            or binding["history_days"] != expected["history_days"]
            or binding["input_manifest_sha256"] != expected["input_manifest_sha256"]
            or row["binding"]["environment"] != self.context["environment"]
            or row["binding"].get("source_population_sha256")
            != self.context["source_population_sha256"]
            or row["code"]["dirty"]
            or row["code"]["files"] != self.context["core_files"]
            or row["source_checkpoint_sha256"] != self.sources[seed]["sha256"]
            or binding["source_checkpoint_sha256"] != self.sources[seed]["sha256"]
        ):
            raise ValueError("Target differs from declared paired Development execution")
        data = self.inputs[binding["history_days"]]
        identity = (*data.namespace, binding["entity_id"])
        if (
            data.entities.get(identity, {}).get("role") != "development"
            or data.binding("target", binding["entity_id"], self.sources[seed]["sha256"]) != binding
        ):
            raise ValueError("Target role/scaler/input differs from accepted Development inputs")
        root = self.study / name
        if list(root.glob(".pending-*")):
            raise ValueError("Uncommitted daily transaction; preserve and inspect")
        saved = json.loads((root / "run.json").read_text())
        if canonical({k: row.get(k) for k in saved}) != canonical(saved):
            raise ValueError("Saved run report differs from execution record")
        return (
            verify_run(root, data.root, input_snapshots=self.snapshots),
            verify_state(root, saved),
        )

    def publish(self, name: str, record: dict, build: Callable[[zipfile.ZipFile], None]) -> None:
        """Receipt is committed only after copied ZIP size/hash/CRC readback passes."""
        safe_name(name)
        archive = self.root / (name + ".zip")
        receipt_path = self.root / (name + ".receipt.json")
        if archive.exists() or receipt_path.exists():
            raise ValueError("Backup identity already exists; never overwrite completed artifacts")
        envelope = {
            "schema": "ev-completed-backup-v1",
            "context_sha256": self.context_sha,
            "name": name,
            "record": record,
        }
        with tempfile.TemporaryDirectory(prefix="ev-backup-") as temp:
            local = Path(temp) / "payload.zip"
            with zipfile.ZipFile(local, "x", compression=zipfile.ZIP_DEFLATED) as output:
                build(output)
                output.writestr("backup-record.json", canonical(envelope))
            with zipfile.ZipFile(local) as output:
                if output.testzip() is not None:
                    raise ValueError("Corrupt local backup")
            pending = self.root / (name + ".zip.pending")
            with local.open("rb") as source, pending.open("xb") as target:
                shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
            checksum = digest(local)
            if pending.stat().st_size != local.stat().st_size or digest(pending) != checksum:
                raise ValueError("Mounted-storage copy differs; no receipt committed")
            with zipfile.ZipFile(pending) as copied:
                if copied.testzip() is not None:
                    raise ValueError("Mounted-storage ZIP CRC differs")
            if archive.exists():
                raise ValueError("Concurrent backup writer; preserve both attempts")
            pending.rename(archive)
            envelope.update(
                bytes=archive.stat().st_size,
                sha256=checksum,
                acceptance="Mounted-filesystem readback only; remote visibility remains external acceptance",
            )
            receipt_pending = self.root / (name + ".receipt.pending")
            with receipt_pending.open("xb") as stream:
                stream.write(canonical(envelope))
                stream.flush()
                os.fsync(stream.fileno())
            receipt_pending.rename(receipt_path)
            if receipt_path.read_bytes() != canonical(envelope):
                raise ValueError("Receipt readback differs")

    def source(self, entry: dict) -> None:
        path = self.check_source(entry)
        seed = entry["seed"]

        def build(output: zipfile.ZipFile) -> None:
            for p in (
                path,
                path.with_name(path.name + ".sha256"),
                path.parent / "run.json",
                self.study / f"source-seed{seed}.log",
                self.study / f"source-seed{seed}-complete.json",
            ):
                put_file(output, "study/" + p.relative_to(self.study).as_posix(), p)

        self.publish(f"source-seed{seed}", {"kind": "source", "entry": entry}, build)
        self.sources[seed] = entry

    def target(self, row: dict) -> None:
        row = json.loads(canonical(row))
        daily, state = self.check_run(row)
        name = row["run_id"]

        def build(output: zipfile.ZipFile) -> None:
            put_run(
                output, self.study, row, state, daily["historical_states_intentionally_omitted"]
            )
            put_file(output, "study/" + name + ".log", self.study / (name + ".log"))

        self.publish(name, {"kind": "target", "entry": row, "daily": daily, "state": state}, build)
        self.runs[name] = row

    def restore(self) -> tuple[list[dict], list[dict]]:
        """Restore only committed receipts into a new study; reverify Source/daily/state."""
        if any(self.study.iterdir()):
            raise ValueError("Restore requires an empty new study directory")
        receipts = list(self.root.glob("*.receipt.json"))
        committed = {p.name.removesuffix(".receipt.json") + ".zip" for p in receipts}
        if {p.name for p in self.root.glob("*.zip")} != committed:
            raise ValueError("Orphan/missing archive; preserve and inspect before resuming")
        records = []
        for receipt in receipts:
            value = json.loads(receipt.read_text())
            name = safe_name(value["name"])
            path = self.root / (name + ".zip")
            if (
                receipt.name != name + ".receipt.json"
                or value["context_sha256"] != self.context_sha
                or path.is_symlink()
                or path.stat().st_size != value["bytes"]
                or digest(path) != value["sha256"]
            ):
                raise ValueError("Changed receipt/context/archive")
            with zipfile.ZipFile(path) as archive:
                envelope = json.loads(archive.read("backup-record.json"))
                if archive.testzip() is not None or any(
                    value.get(k) != v for k, v in envelope.items()
                ):
                    raise ValueError("Archive record differs from receipt")
                if len(archive.namelist()) != len(set(archive.namelist())):
                    raise ValueError("Duplicate archive members")
                for member in archive.infolist():
                    if member.filename == "backup-record.json":
                        continue
                    relative = PurePosixPath(member.filename)
                    if (
                        not relative.parts
                        or relative.parts[0] != "study"
                        or len(relative.parts) < 2
                        or relative.as_posix() != member.filename
                        or member.is_dir()
                        or stat.S_IFMT(member.external_attr >> 16) == stat.S_IFLNK
                    ):
                        raise ValueError("Unsafe/noncanonical backup payload")
                    for component in relative.parts:
                        safe_name(component)
                    destination = self.study.joinpath(*relative.parts[1:])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("xb") as target:
                        shutil.copyfileobj(source, target)
            records.append(value["record"])
        for record in records:
            if record["kind"] == "source":
                entry = record["entry"]
                path = self.check_source(entry)
                seed = entry["seed"]
                if seed in self.sources:
                    raise ValueError("Duplicate Source seed")
                self.sources[seed] = {**entry, "path": str(path)}
            elif record["kind"] != "target":
                raise ValueError("Unknown completed backup kind")
        for record in records:
            if record["kind"] != "target":
                continue
            row = record["entry"]
            daily, state = self.check_run(row)
            if daily != record["daily"] or state != record["state"] or row["run_id"] in self.runs:
                raise ValueError("Restored daily/state proof differs or target duplicated")
            self.runs[row["run_id"]] = row
        return list(self.sources.values()), list(self.runs.values())
