from typing import Literal
from pydantic import BaseModel, Field
from uuid import UUID


class Meta(BaseModel):
    version: str
    start_month: str
    end_month: str
    published_at: str
    demo: bool
    months: list[str]
    source: str = "CRMLS via Trestle"
    units: dict[str, str] = Field(default_factory=lambda: {
        "median_price": "USD", "sales_volume": "USD", "price_sqft": "USD/ft²",
        "days_on_market": "days", "price_ratio": "fraction", "mortgage_rate": "percent",
        "new_listings": "listings", "closed_sales": "sales", "market_share": "fraction",
    })
    refresh_schedule: str = "Monthly · day 7 · 6:00 AM Pacific"


class Metrics(BaseModel):
    new_listings: int = 0
    closed_sales: int = 0
    median_price: float | None = None
    days_on_market: float | None = None
    price_sqft: float | None = None
    price_ratio: float | None = None
    mortgage_rate: float | None = None
    days_sample: int = 0
    sqft_sample: int = 0
    ratio_sample: int = 0


class Summary(BaseModel):
    meta: Meta
    month: str
    current: Metrics
    previous: Metrics | None


class TrendPoint(Metrics):
    month: str


class Trends(BaseModel):
    meta: Meta
    points: list[TrendPoint]


class FilterOptions(BaseModel):
    meta: Meta
    counties: list[str]
    cities: list[str]
    zips: list[str]
    subtypes: list[str]


class Area(BaseModel):
    id: str
    name: str
    value: float | None
    closed_sales: int
    median_price: float | None


class Cell(BaseModel):
    latitude: float
    longitude: float
    count: int


class MapData(BaseModel):
    meta: Meta
    metric: Literal["median_price", "closed_sales", "concentration"]
    level: Literal["county", "zip"]
    areas: list[Area]
    cells: list[Cell]
    unmapped_sales: int


class Entity(BaseModel):
    id: str
    name: str
    closed_sales: int
    sales_volume: float
    median_price: float | None
    market_share: float


class Competitive(BaseModel):
    meta: Meta
    agents: list[Entity]
    offices: list[Entity]
    closed_sales: int
    sales_volume: float


class Filters(BaseModel):
    version: UUID | None = None
    month: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    county: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    zip: str | None = Field(None, pattern=r"^\d{5}$")
    subtype: str | None = Field(None, max_length=100)

class TrendFilters(Filters):
    period: Literal["24","all"] = "24"

class MapFilters(Filters):
    level: Literal["county","zip"] = "county"
    metric: Literal["median_price","closed_sales","concentration"] = "median_price"
