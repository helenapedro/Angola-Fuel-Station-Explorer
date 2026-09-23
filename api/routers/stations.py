"""Station endpoints: list (paginated + filtered), detail, and aggregates."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import StationData, get_station_data
from api.schemas import Station, StationList, Stats

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


def _apply_filters(
    df: pd.DataFrame,
    province: str | None,
    operator: str | None,
    search: str | None,
) -> pd.DataFrame:
    # province/operator are exact (case-insensitive) filters; `search` is the
    # free-text substring match. regex=False keeps user input literal so a
    # value like "(" can't raise re.error and turn into a 500.
    if province:
        wanted = province.strip().lower()
        df = df[df["province"].fillna("").str.strip().str.lower() == wanted]
    if operator:
        wanted = operator.strip().lower()
        df = df[df["operator"].fillna("").str.strip().str.lower() == wanted]
    if search:
        haystacks = (
            df["station"].fillna("")
            + " "
            + df["address"].fillna("")
            + " "
            + df["municipality"].fillna("")
        )
        df = df[haystacks.str.contains(search, case=False, na=False, regex=False)]
    return df


def _to_station(row) -> Station:
    return Station(**{key: row[key] for key in Station.model_fields})


@router.get("", response_model=StationList)
def list_stations(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    province: str | None = Query(None, description="Exact (case-insensitive) province filter"),
    operator: str | None = Query(None, description="Exact (case-insensitive) operator filter"),
    search: str | None = Query(None, description="Free-text search over name, address, municipality"),
    station_data: StationData = Depends(get_station_data),
):
    df, _source = station_data
    df = _apply_filters(df, province, operator, search)

    total = len(df)
    total_pages = max(1, -(-total // page_size))
    start = (page - 1) * page_size
    items = [_to_station(row) for _, row in df.iloc[start : start + page_size].iterrows()]

    return StationList(items=items, page=page, page_size=page_size, total=total, total_pages=total_pages)


@router.get("/stats", response_model=Stats)
def station_stats(station_data: StationData = Depends(get_station_data)):
    df, _source = station_data
    return Stats(
        total_stations=len(df),
        with_coordinates=int(df["latitude"].notna().sum()),
        by_operator=df["operator"].fillna("Unknown").value_counts().to_dict(),
        by_province=df["province"].fillna("Unknown").value_counts().to_dict(),
    )


@router.get("/provinces", response_model=list[str])
def list_provinces(station_data: StationData = Depends(get_station_data)):
    df, _source = station_data
    return sorted(p for p in df["province"].dropna().unique() if p)


@router.get("/operators", response_model=list[str])
def list_operators(station_data: StationData = Depends(get_station_data)):
    df, _source = station_data
    return sorted(o for o in df["operator"].dropna().unique() if o)


# NOTE: this must stay below the fixed sub-paths above — FastAPI matches
# routes in declaration order, so "/{station_id}" would otherwise swallow
# "/stats", "/provinces" and "/operators".
@router.get("/{station_id}", response_model=Station)
def get_station(station_id: int, station_data: StationData = Depends(get_station_data)):
    df, _source = station_data
    match = df[df["id"] == station_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return _to_station(match.iloc[0])
