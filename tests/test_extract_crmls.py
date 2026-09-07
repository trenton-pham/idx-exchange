from __future__ import annotations

import csv
import os
import tempfile
import unittest
from collections import deque
from pathlib import Path
from unittest import mock

import requests

from extract_crmls import (
    ExtractionError,
    LISTING_SPEC,
    PROPERTY_FIELDS,
    SOLD_SPEC,
    Month,
    TrestleClient,
    build_filter,
    export_month,
    extract_range,
    iter_months,
    load_env_file,
    validate_record,
)


API_URL = "https://api.example.test/trestle/odata/Property"
AUTH_ENDPOINT = "https://auth.example.test/token"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, *, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}", response=self  # type: ignore[arg-type]
            )


class QueueSession:
    def __init__(self, *responses):
        self.responses = deque(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


def make_client(session, **kwargs):
    return TrestleClient(
        api_url=API_URL,
        auth_endpoint=AUTH_ENDPOINT,
        session=session,
        sleep=kwargs.pop("sleep", lambda _: None),
        clock=kwargs.pop("clock", lambda: 100.0),
        **kwargs,
    )


class MonthTests(unittest.TestCase):
    def test_month_parsing_and_range_across_year(self):
        months = list(iter_months(Month.parse("2026-11"), Month.parse("2027-02")))
        self.assertEqual(
            [month.label for month in months],
            ["2026-11", "2026-12", "2027-01", "2027-02"],
        )

    def test_month_parser_rejects_non_padded_and_invalid_values(self):
        for value in ("2026-8", "2026-13", "August 2026"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Month.parse(value)

    def test_filters_use_half_open_month_boundaries(self):
        month = Month.parse("2026-08")
        self.assertEqual(
            build_filter(LISTING_SPEC, month),
            "ListingContractDate ge 2026-08-01T00:00:00.000Z and "
            "ListingContractDate lt 2026-09-01T00:00:00.000Z",
        )
        self.assertEqual(
            build_filter(SOLD_SPEC, month),
            "CloseDate ge 2026-08-01T00:00:00.000Z and "
            "CloseDate lt 2026-09-01T00:00:00.000Z "
            "and StandardStatus eq 'Closed'",
        )


class ClientTests(unittest.TestCase):
    def test_analytics_projection_has_no_duplicate_columns(self):
        self.assertEqual(len(PROPERTY_FIELDS), len(set(PROPERTY_FIELDS)))
        downstream_fields = {
            "BathroomsTotalInteger",
            "BedroomsTotal",
            "City",
            "CloseDate",
            "ClosePrice",
            "ContractStatusChangeDate",
            "DaysOnMarket",
            "Latitude",
            "ListAgentFullName",
            "ListOfficeName",
            "ListingContractDate",
            "ListingKey",
            "ListingKeyNumeric",
            "LivingArea",
            "Longitude",
            "OriginalListPrice",
            "PostalCode",
            "PropertySubType",
            "PropertyType",
            "PurchaseContractDate",
            "StateOrProvince",
            "StandardStatus",
        }
        self.assertLessEqual(downstream_fields, set(PROPERTY_FIELDS))

    def test_token_is_cached_between_requests(self):
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            FakeResponse(payload={"value": []}),
            FakeResponse(payload={"value": []}),
        )
        client = make_client(session)

        client.get(API_URL)
        client.get(API_URL)

        self.assertEqual([call[0] for call in session.calls], ["GET", "GET", "GET"])
        self.assertEqual(
            [call[1] for call in session.calls].count(AUTH_ENDPOINT), 1
        )
        self.assertEqual(
            session.calls[1][2]["headers"]["Authorization"], "Bearer token"
        )

    def test_401_refreshes_token_once(self):
        session = QueueSession(
            FakeResponse(payload={"access_token": "old", "expires_in": 3600}),
            FakeResponse(status_code=401),
            FakeResponse(payload={"access_token": "new", "expires_in": 3600}),
            FakeResponse(payload={"value": []}),
        )
        client = make_client(session)

        client.get(API_URL)

        self.assertEqual(
            [call[0] for call in session.calls], ["GET", "GET", "GET", "GET"]
        )
        self.assertEqual(
            [call[1] for call in session.calls].count(AUTH_ENDPOINT), 2
        )
        self.assertEqual(
            session.calls[-1][2]["headers"]["Authorization"], "Bearer new"
        )

    def test_transient_response_uses_retry_after(self):
        sleeps = []
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            FakeResponse(status_code=429, headers={"Retry-After": "3"}),
            FakeResponse(payload={"value": []}),
        )
        client = make_client(session, sleep=sleeps.append)

        client.get(API_URL)

        self.assertEqual(sleeps, [3.0])

    def test_timeout_is_retried(self):
        sleeps = []
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            requests.Timeout("slow response"),
            FakeResponse(payload={"value": []}),
        )
        client = make_client(session, sleep=sleeps.append)

        client.get(API_URL)

        self.assertEqual(sleeps, [1])

    def test_metadata_parser_and_missing_field_validation(self):
        xml = """<?xml version="1.0"?>
        <edmx:Edmx xmlns:edmx="urn:edmx" xmlns="urn:edm">
          <edmx:DataServices><Schema><EntityType Name="Property">
            <Property Name="ListingKey" Type="Edm.String" />
          </EntityType></Schema></edmx:DataServices>
        </edmx:Edmx>"""
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            FakeResponse(text=xml),
        )
        client = make_client(session)

        with self.assertRaisesRegex(ExtractionError, "CloseDate"):
            client.validate_property_fields(("ListingKey", "CloseDate"))

    def test_pagination_follows_next_link_without_reusing_query_params(self):
        next_link = (
            "https://canonical.example.test/trestle/odata/Property?$skip=1"
        )
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            FakeResponse(
                payload={
                    "value": [{"ListingKey": "1"}],
                    "@odata.nextLink": next_link,
                }
            ),
            FakeResponse(payload={"value": [{"ListingKey": "2"}]}),
        )
        client = make_client(session)

        pages = list(
            client.iter_property_pages("CloseDate ge 2026-08-01", ("ListingKey",))
        )

        self.assertEqual(len(pages), 2)
        self.assertIsNotNone(session.calls[1][2]["params"])
        self.assertIsNone(session.calls[2][2]["params"])
        self.assertEqual(session.calls[2][1], f"{API_URL}?$skip=1")

    def test_pagination_rejects_a_different_resource_path(self):
        client = make_client(QueueSession())

        with self.assertRaisesRegex(ExtractionError, "unsafe"):
            client._next_page_url(
                "https://canonical.example.test/trestle/odata/Member?$skip=1"
            )

    def test_env_file_loads_urls_without_overriding_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "CORELOGIC_API_URL=https://file.example.test/Property\n"
                "AUTH_ENDPOINT=https://file-auth.example.test/token\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"CORELOGIC_API_URL": API_URL},
                clear=True,
            ):
                load_env_file(env_path)
                self.assertEqual(os.environ["CORELOGIC_API_URL"], API_URL)
                self.assertEqual(
                    os.environ["AUTH_ENDPOINT"],
                    "https://file-auth.example.test/token",
                )

    def test_client_accepts_api_base_or_property_url(self):
        direct = make_client(QueueSession())
        from_base = TrestleClient(
            api_url="https://api.example.test/trestle/odata",
            auth_endpoint=AUTH_ENDPOINT,
            session=QueueSession(),
        )

        self.assertEqual(direct.property_url, API_URL)
        self.assertEqual(from_base.property_url, API_URL)
        self.assertEqual(
            direct.metadata_url,
            "https://api.example.test/trestle/odata/$metadata",
        )


class ExportTests(unittest.TestCase):
    def test_range_orchestration_validates_metadata_and_writes_both_exports(self):
        class RangeClient:
            validated = False

            def validate_property_fields(self):
                self.validated = True

            def iter_property_pages(self, filter_expression, _fields):
                if filter_expression.startswith("ListingContractDate"):
                    record = {
                        "ListingKey": "listing-1",
                        "ListingContractDate": "2026-08-05",
                    }
                else:
                    record = {
                        "ListingKey": "sold-1",
                        "CloseDate": "2026-08-20",
                        "StandardStatus": "Closed",
                    }
                yield {"@odata.count": 1, "value": [record]}

        client = RangeClient()
        with tempfile.TemporaryDirectory() as directory:
            results = extract_range(
                Month.parse("2026-08"),
                Month.parse("2026-08"),
                Path(directory),
                client=client,  # type: ignore[arg-type]
            )
            output_names = sorted(result.path.name for result in results)

        self.assertTrue(client.validated)
        self.assertEqual(
            output_names, ["CRMLSListing202608.csv", "CRMLSSold202608.csv"]
        )

    def test_multi_page_export_has_stable_field_order(self):
        next_link = f"{API_URL}?$skip=1"
        session = QueueSession(
            FakeResponse(payload={"access_token": "token", "expires_in": 3600}),
            FakeResponse(
                payload={
                    "@odata.count": 2,
                    "@odata.nextLink": next_link,
                    "value": [
                        {
                            "ListingKey": "1",
                            "CloseDate": "2026-08-01",
                            "StandardStatus": "Closed",
                        }
                    ],
                }
            ),
            FakeResponse(
                payload={
                    "value": [
                        {
                            "ListingKey": "2",
                            "CloseDate": "2026-08-31",
                            "StandardStatus": "Closed",
                        }
                    ]
                }
            ),
        )
        fields = ("ListingKey", "CloseDate", "StandardStatus", "City")
        with tempfile.TemporaryDirectory() as directory:
            result = export_month(
                make_client(session),
                SOLD_SPEC,
                Month.parse("2026-08"),
                Path(directory),
                fields=fields,
            )
            with result.path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(result.row_count, 2)
        self.assertEqual(list(rows[0]), list(fields))
        self.assertEqual([row["ListingKey"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["City"], "")

    def test_failed_forced_export_preserves_existing_file_and_removes_temp(self):
        class DuplicateClient:
            def iter_property_pages(self, *_args, **_kwargs):
                yield {
                    "@odata.count": 2,
                    "value": [
                        {
                            "ListingKey": "1",
                            "CloseDate": "2026-08-01",
                            "StandardStatus": "Closed",
                        },
                        {
                            "ListingKey": "1",
                            "CloseDate": "2026-08-02",
                            "StandardStatus": "Closed",
                        },
                    ],
                }

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            output = output_dir / "CRMLSSold202608.csv"
            output.write_text("original\n", encoding="utf-8")
            with self.assertRaisesRegex(ExtractionError, "Duplicate ListingKey"):
                export_month(
                    DuplicateClient(),  # type: ignore[arg-type]
                    SOLD_SPEC,
                    Month.parse("2026-08"),
                    output_dir,
                    force=True,
                    fields=("ListingKey", "CloseDate", "StandardStatus"),
                )
            self.assertEqual(output.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(list(output_dir.glob("*.tmp")), [])

    def test_record_validation_rejects_boundary_and_non_closed_rows(self):
        month = Month.parse("2026-08")
        with self.assertRaisesRegex(ExtractionError, "outside requested month"):
            validate_record(
                {
                    "ListingKey": "1",
                    "CloseDate": "2026-09-01",
                    "StandardStatus": "Closed",
                },
                SOLD_SPEC,
                month,
                set(),
            )
        with self.assertRaisesRegex(ExtractionError, "not a closed record"):
            validate_record(
                {
                    "ListingKey": "2",
                    "CloseDate": "2026-08-31",
                    "StandardStatus": "Pending",
                },
                SOLD_SPEC,
                month,
                set(),
            )

    def test_existing_complete_month_skips_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            (output_dir / "CRMLSListing202608.csv").write_text("header\n")
            (output_dir / "CRMLSSold202608.csv").write_text("header\n")
            results = extract_range(
                Month.parse("2026-08"), Month.parse("2026-08"), output_dir
            )
        self.assertTrue(all(result.skipped for result in results))


if __name__ == "__main__":
    unittest.main()
