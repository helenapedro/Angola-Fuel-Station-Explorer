"""Build clean and rejected station datasets from all configured sources."""

import argparse
import json
from pathlib import Path

from ingestion.normalize import normalize_legacy_pumangol, utc_now_iso
from ingestion.validate import split_valid_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
LEGACY_FALLBACK_PATH = PROJECT_ROOT / "gas_stations.json"
CLEAN_OUTPUT_PATH = DATA_DIR / "stations_clean.json"
REJECTED_OUTPUT_PATH = DATA_DIR / "stations_rejected.json"
LEGACY_SOURCE_NAME = "BundledLegacyPumangol"


def build_dataset(include_network_sources=True, previous_clean_path=CLEAN_OUTPUT_PATH):
    records = []
    source_status = []

    if LEGACY_FALLBACK_PATH.exists():
        legacy_records = _load_legacy_records(LEGACY_FALLBACK_PATH)
        records.extend(legacy_records)
        source_status.append(
            {
                "source": LEGACY_SOURCE_NAME,
                "status": "loaded",
                "record_count": len(legacy_records),
                "is_stale": False,
            }
        )

    if include_network_sources:
        from ingestion.sources.osm import fetch_osm_stations
        from ingestion.sources.pumangol import fetch_pumangol_stations
        from ingestion.sources.sonangol import fetch_sonangol_stations

        for source_name, fetcher in (
            ("OpenStreetMap", fetch_osm_stations),
            ("SonangolOpenStreetMap", fetch_sonangol_stations),
            ("Pumangol", fetch_pumangol_stations),
        ):
            try:
                source_records = fetcher()
                records.extend(source_records)
                source_status.append(
                    {
                        "source": source_name,
                        "status": "loaded",
                        "record_count": len(source_records),
                        "is_stale": False,
                    }
                )
            except Exception as exc:
                stale_records = _load_previous_source_records(previous_clean_path, source_name, str(exc))
                records.extend(stale_records)
                source_status.append(
                    {
                        "source": source_name,
                        "status": "stale_reused" if stale_records else "failed",
                        "record_count": len(stale_records),
                        "is_stale": bool(stale_records),
                        "error": str(exc),
                    }
                )

    clean_records, rejected_records = split_valid_records(records)
    generated_at = utc_now_iso()
    metadata = {
        "generated_at": generated_at,
        "record_count": len(clean_records),
        "rejected_count": len(rejected_records),
        "source_status": source_status,
        "source_errors": [status for status in source_status if status["status"] in {"failed", "stale_reused"}],
    }
    return {"metadata": metadata, "stations": clean_records}, {"metadata": metadata, "stations": rejected_records}


def write_dataset(clean_payload, rejected_payload):
    DATA_DIR.mkdir(exist_ok=True)
    CLEAN_OUTPUT_PATH.write_text(json.dumps(clean_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REJECTED_OUTPUT_PATH.write_text(json.dumps(rejected_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Refresh validated station data.")
    parser.add_argument("--offline", action="store_true", help="Build only from the bundled legacy JSON.")
    parser.add_argument("--check", action="store_true", help="Validate dataset generation without writing output files.")
    args = parser.parse_args()

    clean_payload, rejected_payload = build_dataset(include_network_sources=not args.offline)
    if not args.check:
        write_dataset(clean_payload, rejected_payload)
    print(
        ("Validated " if args.check else "Generated ")
        + f"{clean_payload['metadata']['record_count']} clean records and "
        + f"{clean_payload['metadata']['rejected_count']} rejected records."
    )


def _load_legacy_records(path):
    scraped_at = utc_now_iso()
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for record in payload:
        normalized_record = normalize_legacy_pumangol(record, scraped_at=scraped_at)
        normalized_record["source_type"] = "legacy_snapshot"
        normalized_record["source_name"] = LEGACY_SOURCE_NAME
        records.append(normalized_record)
    return records


def _load_previous_source_records(path, source_name, stale_reason):
    if not path or not Path(path).exists():
        return []

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("stations", []) if isinstance(payload, dict) else []
    stale_records = []
    for record in records:
        if record.get("source_name") != source_name:
            continue
        stale_record = dict(record)
        stale_record["is_stale"] = True
        stale_record["stale_reason"] = stale_reason
        stale_records.append(stale_record)
    return stale_records


if __name__ == "__main__":
    main()
