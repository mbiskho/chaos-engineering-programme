from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .faults import manifest
from .spec import Experiment
from .steady import Prometheus


def kubectl(args: list[str], stdin: str | None = None) -> None:
    subprocess.run(["kubectl", *args], input=stdin, text=True, check=True, capture_output=True)


def run(e: Experiment, prom: Prometheus, results_dir: Path, dry_run: bool = False) -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    doc = manifest(e, run_id)
    if dry_run:
        print(yaml.safe_dump(doc, sort_keys=False))
        return {"result": "dry-run"}

    record = {"experiment": e.name, "hypothesis": e.hypothesis, "run_id": run_id,
              "started": datetime.now(timezone.utc).isoformat(), "timeline": []}
    log = lambda msg, **kw: record["timeline"].append({"t": time.time(), "msg": msg, **kw})  # noqa: E731

    before = prom.evaluate(e.steady_state)
    log("steady state before", checks=[(c.name, v, ok) for c, v, ok in before])
    if not all(ok for _, _, ok in before):
        record["result"] = "not-started"
        record["reason"] = "system was not in steady state before the experiment"
        return save(record, results_dir)

    aborted = None
    try:
        kubectl(["apply", "-f", "-"], stdin=yaml.safe_dump(doc))
        log("fault injected", kind=doc["kind"])
        deadline = time.monotonic() + e.duration_seconds
        while time.monotonic() < deadline:
            time.sleep(10)
            # An abort condition is phrased as "abort if X"; it trips when the condition holds.
            tripped = [(c.name, v) for c, v, ok in prom.evaluate(e.abort_if) if ok]
            if tripped:
                aborted = tripped
                log("ABORT", tripped=tripped)
                break
    finally:
        kubectl(["delete", doc["kind"].lower(), doc["metadata"]["name"], "-n", e.namespace, "--ignore-not-found"])
        log("fault removed")

    time.sleep(e.recovery_seconds)
    after = prom.evaluate(e.steady_state)
    log("steady state after", checks=[(c.name, v, ok) for c, v, ok in after])
    if aborted:
        record["result"] = "aborted"
    else:
        record["result"] = "hypothesis-held" if all(ok for _, _, ok in after) else "hypothesis-refuted"
    return save(record, results_dir)


def save(record: dict, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{record['experiment']}-{record['run_id']}.json").write_text(json.dumps(record, indent=2, default=str))
    return record
