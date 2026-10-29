"""Dataset metadata endpoint: the public contract for freshness.

``GET /api/v1/meta`` returns the same metadata the Dash badge shows,
because both call :func:`dataset_meta.load_dataset_meta`. The endpoint
never invents a date: if the snapshot metadata is missing or its
``generated_at`` is unusable, the response reports
``freshness_status="unavailable"`` instead of a date.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

import dataset_meta
from api.deps import StationData, get_station_data
from api.schemas import DatasetMeta

router = APIRouter(tags=["meta"])


@router.get("/api/v1/meta", response_model=DatasetMeta)
def dataset_metadata(station_data: StationData = Depends(get_station_data)):
    _df, source = station_data
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    if meta is None:
        return DatasetMeta(
            version_id=None,
            snapshot_origin=dataset_meta.SNAPSHOT_ORIGIN,
            generated_at=None,
            record_count=None,
            rejected_count=None,
            source=source,
            freshness_status="unavailable",
            is_stale=None,
            age_days=None,
            fresh=False,
            fresh_threshold_days=dataset_meta.FRESH_THRESHOLD_DAYS,
            source_status=[],
            confidence_counts=None,
        )
    return DatasetMeta(
        version_id=meta["version_id"],
        snapshot_origin=meta["snapshot_origin"],
        generated_at=meta["generated_at"],
        record_count=meta["record_count"],
        rejected_count=meta["rejected_count"],
        source=source,
        freshness_status=meta["freshness_status"],
        is_stale=meta["is_stale"],
        age_days=meta["age_days"],
        fresh=meta["fresh"],
        fresh_threshold_days=dataset_meta.FRESH_THRESHOLD_DAYS,
        source_status=meta["source_status"],
        confidence_counts=meta["confidence_counts"],
    )
