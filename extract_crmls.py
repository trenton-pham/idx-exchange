"""Extract monthly CRMLS listing and sold datasets from Trestle WebAPI."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlparse
from uuid import uuid4

import requests


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
ENV_PATH = PROJECT_DIR / ".env"

PAGE_SIZE = 1000
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Ordered, de-duplicated union of the July 2026 listing and sold exports. Contact
# email and retired compensation fields are deliberately excluded.
PROPERTY_FIELDS = (
    "BuyerAgentAOR",
    "ListAgentAOR",
    "Flooring",
    "ViewYN",
    "WaterfrontYN",
    "BasementYN",
    "PoolPrivateYN",
    "OriginalListPrice",
    "ListingKey",
    "CloseDate",
    "ClosePrice",
    "ListAgentFirstName",
    "ListAgentLastName",
    "Latitude",
    "Longitude",
    "UnparsedAddress",
    "PropertyType",
    "LivingArea",
    "ListPrice",
    "DaysOnMarket",
    "ListOfficeName",
    "BuyerOfficeName",
    "CoListOfficeName",
    "ListAgentFullName",
    "CoListAgentFirstName",
    "CoListAgentLastName",
    "BuyerAgentMlsId",
    "BuyerAgentFirstName",
    "BuyerAgentLastName",
    "FireplacesTotal",
    "AssociationFeeFrequency",
    "AboveGradeFinishedArea",
    "ListingKeyNumeric",
    "MLSAreaMajor",
    "TaxAnnualAmount",
    "CountyOrParish",
    "MlsStatus",
    "ElementarySchool",
    "AttachedGarageYN",
    "ParkingTotal",
    "BuilderName",
    "PropertySubType",
    "LotSizeAcres",
    "SubdivisionName",
    "BuyerOfficeAOR",
    "YearBuilt",
    "StreetNumberNumeric",
    "ListingId",
    "BathroomsTotalInteger",
    "City",
    "TaxYear",
    "BuildingAreaTotal",
    "BedroomsTotal",
    "ContractStatusChangeDate",
    "ElementarySchoolDistrict",
    "CoBuyerAgentFirstName",
    "PurchaseContractDate",
    "ListingContractDate",
    "BelowGradeFinishedArea",
    "BusinessType",
    "StateOrProvince",
    "CoveredSpaces",
    "MiddleOrJuniorSchool",
    "FireplaceYN",
    "Stories",
    "HighSchool",
    "Levels",
    "LotSizeDimensions",
    "LotSizeArea",
    "MainLevelBedrooms",
    "NewConstructionYN",
    "GarageSpaces",
    "HighSchoolDistrict",
    "PostalCode",
    "AssociationFee",
    "LotSizeSquareFeet",
    "MiddleOrJuniorSchoolDistrict",
    "OriginatingSystemName",
    "OriginatingSystemSubName",
    "StandardStatus",
)


class ExtractionError(RuntimeError):
    """Raised when an API response or extracted dataset fails validation."""


@dataclass(frozen=True, order=True)
class Month:
    year: int
    month: int

    @classmethod
    def parse(cls, value: str) -> "Month":
        match = MONTH_PATTERN.fullmatch(value)
        if not match:
            raise ValueError(f"Invalid month {value!r}; expected YYYY-MM.")

        year, month = (int(part) for part in match.groups())
        if year < 1 or not 1 <= month <= 12:
            raise ValueError(
                f"Invalid month {value!r}; use a positive year and month 01 through 12."
            )
        return cls(year, month)

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def compact(self) -> str:
        return f"{self.year:04d}{self.month:02d}"

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def next(self) -> "Month":
        if self.month == 12:
            return Month(self.year + 1, 1)
        return Month(self.year, self.month + 1)


@dataclass(frozen=True)
class DatasetSpec:
    label: str
    filename_prefix: str
    date_field: str
    closed_only: bool = False


@dataclass(frozen=True)
class ExportResult:
    path: Path
    row_count: int | None
    skipped: bool


LISTING_SPEC = DatasetSpec("listings", "CRMLSListing", "ListingContractDate")
SOLD_SPEC = DatasetSpec("sold records", "CRMLSSold", "CloseDate", closed_only=True)
DATASET_SPECS = (LISTING_SPEC, SOLD_SPEC)


def iter_months(start: Month, end: Month) -> Iterator[Month]:
    if end < start:
        raise ValueError("End month must not be earlier than start month.")

    current = start
    while current <= end:
        yield current
        current = current.next()


def build_filter(spec: DatasetSpec, month: Month) -> str:
    start = f"{month.first_day.isoformat()}T00:00:00.000Z"
    end = f"{month.next().first_day.isoformat()}T00:00:00.000Z"
    clauses = [f"{spec.date_field} ge {start}", f"{spec.date_field} lt {end}"]
    if spec.closed_only:
        clauses.append("StandardStatus eq 'Closed'")
    return " and ".join(clauses)


def load_env_file(path: Path = ENV_PATH) -> None:
    """Load simple KEY=VALUE settings without replacing shell environment values."""
    if not path.exists():
        return

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not ENV_NAME_PATTERN.fullmatch(name):
            raise ExtractionError(
                f"Invalid .env setting on line {line_number}; expected KEY=VALUE."
            )
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def _validated_https_url(value: str | None, setting_name: str) -> str:
    if not value:
        raise ExtractionError(f"{setting_name} must be set in .env or the shell.")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ExtractionError(f"{setting_name} must be a valid HTTPS URL.")
    return value.rstrip("/")


class TrestleClient:
    """Trestle client using the team's token proxy and bounded retries."""

    def __init__(
        self,
        *,
        api_url: str | None = None,
        auth_endpoint: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        max_attempts: int = 5,
    ) -> None:
        if api_url is None or auth_endpoint is None:
            load_env_file()

        configured_api_url = _validated_https_url(
            api_url or os.environ.get("CORELOGIC_API_URL"), "CORELOGIC_API_URL"
        )
        if urlparse(configured_api_url).path.rstrip("/").endswith("/Property"):
            self.property_url = configured_api_url
        else:
            self.property_url = f"{configured_api_url}/Property"
        self.metadata_url = f"{self.property_url.rsplit('/', 1)[0]}/$metadata"
        self.auth_endpoint = _validated_https_url(
            auth_endpoint or os.environ.get("AUTH_ENDPOINT"), "AUTH_ENDPOINT"
        )
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.max_attempts = max_attempts
        self.timeout = (10, 120)
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def _retry_delay(self, response: requests.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(max(float(retry_after), 0.0), 60.0)
                except ValueError:
                    pass
        return min(2**attempt, 30)

    def _request_with_retries(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            response: requests.Response | None = None
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
            except requests.RequestException as error:
                last_error = error
            else:
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    return response
                last_error = ExtractionError(
                    f"Trestle returned transient HTTP {response.status_code}."
                )

            if attempt + 1 < self.max_attempts:
                self.sleep(self._retry_delay(response, attempt))

        raise ExtractionError(
            f"Trestle request failed after {self.max_attempts} attempts."
        ) from last_error

    def _authenticate(self) -> str:
        response = self._request_with_retries(
            "GET",
            self.auth_endpoint,
            headers={
                "Accept": "application/json",
                "User-Agent": "IDXExchangeCRMLSExtractor/1.0",
            },
        )
        try:
            response.raise_for_status()
            payload = response.json()
            token = payload["access_token"]
            expires_in = float(payload.get("expires_in", 28_800))
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            raise ExtractionError("Trestle authentication failed.") from error

        if not isinstance(token, str) or not token:
            raise ExtractionError("Trestle authentication returned an invalid token.")

        self._access_token = token
        self._token_expires_at = self.clock() + max(expires_in - 60, 1)
        return token

    def _token(self) -> str:
        if self._access_token and self.clock() < self._token_expires_at:
            return self._access_token
        return self._authenticate()

    def get(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> requests.Response:
        for auth_attempt in range(2):
            response = self._request_with_retries(
                "GET",
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._token()}",
                    "User-Agent": "IDXExchangeCRMLSExtractor/1.0",
                },
            )
            if response.status_code == 401 and auth_attempt == 0:
                self._access_token = None
                self._token_expires_at = 0.0
                continue
            try:
                response.raise_for_status()
            except requests.RequestException as error:
                raise ExtractionError(
                    f"Trestle request returned HTTP {response.status_code}."
                ) from error
            return response
        raise ExtractionError("Trestle rejected the refreshed access token.")

    def get_metadata_fields(self) -> set[str]:
        response = self.get(self.metadata_url)
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as error:
            raise ExtractionError("Trestle returned invalid metadata XML.") from error

        for element in root.iter():
            if _local_name(element.tag) != "EntityType":
                continue
            if element.attrib.get("Name") != "Property":
                continue
            return {
                child.attrib["Name"]
                for child in element
                if _local_name(child.tag) == "Property" and "Name" in child.attrib
            }
        raise ExtractionError("Property resource was not found in Trestle metadata.")

    def validate_property_fields(self, fields: Sequence[str] = PROPERTY_FIELDS) -> None:
        available = self.get_metadata_fields()
        missing = sorted(set(fields) - available)
        if missing:
            raise ExtractionError(
                "Trestle metadata is missing required fields: " + ", ".join(missing)
            )

    def iter_property_pages(
        self, filter_expression: str, fields: Sequence[str] = PROPERTY_FIELDS
    ) -> Iterator[dict[str, Any]]:
        url = self.property_url
        params: Mapping[str, str] | None = {
            "$filter": filter_expression,
            "$select": ",".join(fields),
            "$top": str(PAGE_SIZE),
            "$count": "true",
        }
        seen_links: set[str] = set()

        while True:
            response = self.get(url, params=params)
            try:
                payload = response.json()
            except ValueError as error:
                raise ExtractionError("Trestle returned invalid JSON.") from error
            if not isinstance(payload, dict) or not isinstance(
                payload.get("value"), list
            ):
                raise ExtractionError(
                    "Trestle response is missing the OData value array."
                )
            yield payload

            next_link = payload.get("@odata.nextLink")
            if not next_link:
                return
            if not isinstance(next_link, str):
                raise ExtractionError("Trestle returned an invalid @odata.nextLink.")
            next_page_url = self._next_page_url(next_link)
            if next_page_url in seen_links:
                raise ExtractionError("Trestle returned a repeated @odata.nextLink.")
            seen_links.add(next_page_url)
            url = next_page_url
            params = None

    def _next_page_url(self, next_link: str) -> str:
        """Keep Trestle's paging query while pinning requests to the configured API."""
        expected = urlparse(self.property_url)
        actual = urlparse(next_link)
        if (
            actual.scheme != "https"
            or not actual.netloc
            or actual.username is not None
            or actual.password is not None
            or actual.fragment
            or actual.path.rstrip("/") != expected.path.rstrip("/")
            or not actual.query
        ):
            raise ExtractionError("Trestle returned an unsafe @odata.nextLink.")
        return f"{self.property_url}?{actual.query}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_record_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ExtractionError(f"Record is missing required date field {field}.")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as error:
        raise ExtractionError(f"Record contains invalid {field}: {value!r}.") from error


def _serialize_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def validate_record(
    record: Mapping[str, Any], spec: DatasetSpec, month: Month, seen_keys: set[str]
) -> None:
    listing_key = record.get("ListingKey")
    if listing_key is None or str(listing_key) == "":
        raise ExtractionError("Trestle record is missing ListingKey.")
    key = str(listing_key)
    if key in seen_keys:
        raise ExtractionError(f"Duplicate ListingKey returned by Trestle: {key}.")
    seen_keys.add(key)

    record_date = _parse_record_date(record.get(spec.date_field), spec.date_field)
    if not month.first_day <= record_date < month.next().first_day:
        raise ExtractionError(
            f"ListingKey {key} falls outside requested month {month.label}."
        )
    if spec.closed_only and record.get("StandardStatus") != "Closed":
        raise ExtractionError(f"ListingKey {key} is not a closed record.")


def export_month(
    client: TrestleClient,
    spec: DatasetSpec,
    month: Month,
    output_dir: Path,
    *,
    force: bool = False,
    fields: Sequence[str] = PROPERTY_FIELDS,
) -> ExportResult:
    output_path = output_dir / f"{spec.filename_prefix}{month.compact}.csv"
    if output_path.exists() and not force:
        print(f"Skipping existing {output_path.name}.")
        return ExportResult(output_path, None, True)

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.{uuid4().hex}.tmp")
    expected_count: int | None = None
    row_count = 0
    seen_keys: set[str] = set()

    try:
        with temp_path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for page_number, payload in enumerate(
                client.iter_property_pages(build_filter(spec, month), fields), start=1
            ):
                if page_number == 1:
                    count_value = payload.get("@odata.count")
                    if not isinstance(count_value, int) or count_value < 0:
                        raise ExtractionError(
                            "First Trestle page is missing a valid @odata.count."
                        )
                    expected_count = count_value

                for record in payload["value"]:
                    if not isinstance(record, dict):
                        raise ExtractionError(
                            "Trestle value array contains a non-object."
                        )
                    validate_record(record, spec, month, seen_keys)
                    writer.writerow(
                        {
                            field: _serialize_csv_value(record.get(field))
                            for field in fields
                        }
                    )
                    row_count += 1

        if expected_count is None or row_count != expected_count:
            raise ExtractionError(
                f"Expected {expected_count} {spec.label}, but downloaded {row_count}."
            )
        os.replace(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    print(f"Wrote {row_count:,} {spec.label} to {output_path.name}.")
    return ExportResult(output_path, row_count, False)


def extract_range(
    start: Month,
    end: Month,
    output_dir: Path = RAW_DIR,
    *,
    force: bool = False,
    client: TrestleClient | None = None,
) -> list[ExportResult]:
    months = list(iter_months(start, end))
    pending = [
        (month, spec)
        for month in months
        for spec in DATASET_SPECS
        if force
        or not (output_dir / f"{spec.filename_prefix}{month.compact}.csv").exists()
    ]
    results: list[ExportResult] = []
    if not pending:
        for month in months:
            for spec in DATASET_SPECS:
                path = output_dir / f"{spec.filename_prefix}{month.compact}.csv"
                print(f"Skipping existing {path.name}.")
                results.append(ExportResult(path, None, True))
        return results

    api_client = client or TrestleClient()
    api_client.validate_property_fields()
    total_exports = len(months) * len(DATASET_SPECS)
    export_number = 0
    for month in months:
        for spec in DATASET_SPECS:
            export_number += 1
            print(
                f"[{export_number}/{total_exports}] Processing {spec.label} "
                f"for {month.label}.",
                flush=True,
            )
            results.append(
                export_month(api_client, spec, month, output_dir, force=force)
            )
    return results


def _month_argument(value: str) -> Month:
    try:
        return Month.parse(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract monthly CRMLS listings and sold records from Trestle."
    )
    parser.add_argument(
        "--start-month",
        required=True,
        type=_month_argument,
        help="first month to fetch (YYYY-MM); ranges may span multiple years",
    )
    parser.add_argument(
        "--end-month",
        required=True,
        type=_month_argument,
        help="last month to fetch, inclusive (YYYY-MM)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace existing monthly CSVs after successful validation",
    )
    args = parser.parse_args(argv)
    if args.end_month < args.start_month:
        parser.error("--end-month must not be earlier than --start-month")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    extract_range(args.start_month, args.end_month, force=args.force)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExtractionError, ValueError) as error:
        print(f"Extraction failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\nExtraction cancelled.", file=sys.stderr)
        raise SystemExit(130)
