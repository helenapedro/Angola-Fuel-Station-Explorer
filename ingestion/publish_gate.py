"""Publication gate for the scheduled ingestion workflow.

The gate runs after ingestion and tests, before the auto-commit step,
so a bad snapshot never reaches the repository: the previous snapshot
stays in production, its age grows, and the public stale warning
appears on its own after 14 days. Blocking rules, from the Phase 0
design:

- no ``generated_at``, or a ``generated_at`` in the future;
- ``record_count`` is zero;
- ``record_count`` drops more than 30% against the previous snapshot
  without a recorded explanation (there is no explanation channel in
  Phase 0, so any such drop blocks and needs manual review);
- ``rejected_count`` rises more than 50% against the previous snapshot.

Standard library only. The command-line form reads the new snapshot
file and a previous snapshot file (extracted from git in the workflow)
and exits non-zero with the blocking reasons on stdout when the gate
fails, so the workflow stops before committing.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_RECORD_DROP_FRACTION = 0.30
MAX_REJECTED_INCREASE_FRACTION = 0.50


def _parse_generated_at(raw):
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def evaluate(new_meta, previous_meta=None, now=None):
    """Return the list of blocking reasons; empty means publish."""
    now = now or datetime.now(timezone.utc)
    reasons = []
    new_meta = new_meta or {}
    generated_at = _parse_generated_at(new_meta.get("generated_at"))
    if generated_at is None:
        reasons.append("generated_at is missing or unparseable.")
    elif generated_at > now:
        reasons.append("generated_at is in the future.")
    record_count = new_meta.get("record_count")
    if not isinstance(record_count, int) or record_count <= 0:
        reasons.append("record_count is zero or missing.")
    if previous_meta:
        previous_count = previous_meta.get("record_count")
        if (
            isinstance(record_count, int)
            and isinstance(previous_count, int)
            and previous_count > 0
            and record_count < previous_count * (1 - MAX_RECORD_DROP_FRACTION)
        ):
            reasons.append(
                f"record_count dropped from {previous_count} to {record_count} "
                f"(more than {int(MAX_RECORD_DROP_FRACTION * 100)}%); manual review required."
            )
        previous_rejected = previous_meta.get("rejected_count")
        rejected_count = new_meta.get("rejected_count")
        if (
            isinstance(rejected_count, int)
            and isinstance(previous_rejected, int)
            and previous_rejected >= 0
            and rejected_count
            > previous_rejected * (1 + MAX_REJECTED_INCREASE_FRACTION)
        ):
            reasons.append(
                f"rejected_count rose from {previous_rejected} to {rejected_count} "
                f"(more than {int(MAX_REJECTED_INCREASE_FRACTION * 100)}%); manual review required."
            )
    return reasons


def _read_metadata(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(payload, dict):
        return payload.get("metadata") or {}
    return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a new snapshot before publication.")
    parser.add_argument("--new", required=True, help="Path to the new stations_clean.json.")
    parser.add_argument("--previous", help="Path to the previous stations_clean.json (optional).")
    args = parser.parse_args(argv)
    new_meta = _read_metadata(args.new)
    previous_meta = _read_metadata(args.previous) if args.previous else None
    reasons = evaluate(new_meta, previous_meta)
    if reasons:
        print("Publication gate blocked:")
        for reason in reasons:
            print(f"  - {reason}")
        return 1
    print("Publication gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
