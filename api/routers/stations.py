"""Station endpoints: list (paginated + filtered), detail, and aggregates."""

from fastapi import APIRouter, HTTPException, Query

from api import db
from api.schemas import Station, StationList, Stats

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


def _apply_filters(df, province: str | None, operator: str | None, search: str | None):
    if province:
        df = df[df["province"].fillna("").str.contains(province, case=False, na=False)]
    if operator:
        df = df[df["operator"].fillna("").str.contains(operator, case=False, na=False)]
    if search:
        haystacks = (
            df["station"].fillna("")
            + " "
            + df["address"].fillna("")
            + " "
            + df["municipality"].fillna("")
        )
        df = df[haystacks.str.contains(search, case=False, na=False)]
    return df


def _to_station(row) -> Station:
    return Station(**{key: row[key] for key in Station.model_fields})


@router.get("", response_model=StationList)
def list_stations(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    province: str | None = Query(None, description="Case-insensitive province filter"),
    operator: str | None = Query(None, description="Case-insensitive operator filter"),
    search: str | None = Query(None, description="Free-text search over name, address, municipality"),
):
    df, _source = db.load_stations_df()
    df = _apply_filters(df, province, operator, search)

    total = len(df)
    total_pages = max(1, -(-total // page_size))
    start = (page - 1) * page_size
    items = [_to_station(row) for _, row in df.iloc[start : start + page_size].iterrows()]

    return StationList(items=items, page=page, page_size=page_size, total=total, total_pages=total_pages)


@router.get("/stats", response_model=Stats)
def station_stats():
    df, _source = db.load_stations_df()
    return Stats(
        total_stations=len(df),
        with_coordinates=int(df["latitude"].notna().sum()),
        by_operator=df["operator"].fillna("Unknown").value_counts().to_dict(),
        by_province=df["province"].fillna("Unknown").value_counts().to_dict(),
    )


@router.get("/provinces", response_model=list[str])
def list_provinces():
    df, _source = db.load_stations_df()
    return sorted(p for p in df["province"].dropna().unique() if p)


@router.get("/operators", response_model=list[str])
def list_operators():
    df, _source = db.load_stations_df()
    return sorted(o for o in df["operator"].dropna().unique() if o)


@router.get("/{station_id}", response_model=Station)
def get_station(station_id: int):
    df, _source = db.load_stations_df()
    match = df[df["id"] == station_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return _to_station(match.iloc[0])
