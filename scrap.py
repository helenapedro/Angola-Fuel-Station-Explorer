"""Compatibility wrapper for refreshing station fallback data.

New ingestion work should use `python -m ingestion.sync_stations`.
"""

from ingestion.sync_stations import main


if __name__ == "__main__":
    main()
