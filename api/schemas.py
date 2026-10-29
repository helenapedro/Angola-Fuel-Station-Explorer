"""Pydantic response models for the stations API."""

from pydantic import BaseModel


class Station(BaseModel):
    id: int
    station: str | None = None
    operator: str | None = None
    address: str | None = None
    municipality: str | None = None
    province: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class StationList(BaseModel):
    items: list[Station]
    page: int
    page_size: int
    total: int
    total_pages: int


class Stats(BaseModel):
    total_stations: int
    with_coordinates: int
    by_operator: dict[str, int]
    by_province: dict[str, int]


class Health(BaseModel):
    status: str
    version: str
    stations: int
    source: str


class SourceStatus(BaseModel):
    source: str
    status: str
    record_count: int = 0
    is_stale: bool = False


class DatasetMeta(BaseModel):
    version_id: str | None = None
    snapshot_origin: str
    generated_at: str | None = None
    record_count: int | None = None
    rejected_count: int | None = None
    source: str
    freshness_status: str
    is_stale: bool | None = None
    age_days: int | None = None
    fresh: bool
    fresh_threshold_days: int
    source_status: list[SourceStatus] = []
    confidence_counts: dict[str, int] | None = None
