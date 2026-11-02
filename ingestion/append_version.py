"""Append the current snapshot to the dataset version registry.

Run by the refresh workflow after the publication gate passes and
before auto-commit, so the version entry and the snapshot land in the
same commit. Idempotent on ``generated_at``: re-running for the same
snapshot leaves the registry unchanged. Standard library only, apart
from the shared ``dataset_versions`` module.
"""

import json
from pathlib import Path

from dataset_versions import VERSIONS_PATH, append_version_entry, read_versions_file

CLEAN_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "stations_clean.json"


def main():
    payload = json.loads(CLEAN_DATA_PATH.read_text(encoding="utf-8"))
    versions = read_versions_file(VERSIONS_PATH)
    updated, entry, appended = append_version_entry(versions, payload.get("metadata"))
    if appended:
        VERSIONS_PATH.parent.mkdir(exist_ok=True)
        VERSIONS_PATH.write_text(
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Appended dataset version {entry['version_id']}.")
    else:
        print(f"Dataset version {entry['version_id']} already recorded; nothing appended.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
