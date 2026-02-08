from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pandas as pd

from server.domain.tables import importers
from server.domain.tables.types import ImportFormat, ReferenceTableColumnInput, TableDataType


def _attachment(path, *, filename: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        storage_path=str(path),
        filename=filename or path.name,
    )


def test_parse_csv_detects_delimiter_and_explicit_delimiter(tmp_path):
    autodetect_path = tmp_path / "campaign_export.csv"
    autodetect_path.write_text("Campaign Name;Spend ($)\nSpring;$1,234.50\n", encoding="utf-8")
    parsed = importers.parse_attachment(
        _attachment(autodetect_path),
        source_format=None,
        has_header=True,
        delimiter=None,
    )

    assert parsed.source_format == ImportFormat.CSV
    assert parsed.dataset_name_suggestion == "campaign_export"
    assert parsed.rows[0]["Campaign_Name"] == "Spring"
    assert parsed.rows[0]["Spend"] == 1234.5
    assert parsed.source_columns["Campaign_Name"] == "Campaign Name"
    assert parsed.source_columns["Spend"] == "Spend ($)"

    explicit_path = tmp_path / "campaign_pipe.csv"
    explicit_path.write_text("Campaign|Impressions\nSpring|1,200\n", encoding="utf-8")
    explicit = importers.parse_attachment(
        _attachment(explicit_path),
        source_format=ImportFormat.CSV,
        has_header=True,
        delimiter="|",
    )
    assert explicit.rows[0]["Campaign"] == "Spring"
    assert explicit.rows[0]["Impressions"] == 1200


def test_parse_csv_normalizes_headers_and_dedupes(tmp_path):
    path = tmp_path / "dup_headers.csv"
    path.write_text("Campaign Name,Campaign Name,\nA,B,C\n", encoding="utf-8")

    parsed = importers.parse_attachment(
        _attachment(path),
        source_format=ImportFormat.CSV,
        has_header=True,
        delimiter=",",
    )

    assert parsed.rows[0]["Campaign_Name"] == "A"
    assert parsed.rows[0]["Campaign_Name_2"] == "B"
    assert parsed.rows[0]["column_3"] == "C"
    assert parsed.source_columns["Campaign_Name"] == "Campaign Name"
    assert parsed.source_columns["Campaign_Name_2"] == "Campaign Name"
    assert parsed.source_columns["column_3"] == "column_3"


def test_parse_json_flattens_nested_records(tmp_path):
    path = tmp_path / "nested.json"
    payload = {
        "rows": [
            {
                "campaign": {"name": "Spring"},
                "metrics": {"spend": "$1,200", "ctr": "12%"},
                "tags": ["retargeting", "search"],
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = importers.parse_attachment(
        _attachment(path),
        source_format=ImportFormat.JSON,
        has_header=True,
        delimiter=None,
    )

    row = parsed.rows[0]
    assert row["campaign_name"] == "Spring"
    assert row["metrics_spend"] == 1200
    assert row["metrics_ctr"] == 0.12
    assert row["tags"] == ["retargeting", "search"]
    assert parsed.source_columns["campaign_name"] == "campaign.name"


def test_parse_xlsx_reads_first_sheet_with_pandas(tmp_path):
    path = tmp_path / "book.xlsx"
    frame = pd.DataFrame({"Campaign": ["Spring"], "Impressions": [42]})
    frame.to_excel(path, index=False)

    parsed = importers.parse_attachment(
        _attachment(path),
        source_format=None,
        has_header=True,
        delimiter=None,
    )

    assert parsed.source_format == ImportFormat.XLSX
    assert parsed.rows[0]["Campaign"] == "Spring"
    assert parsed.rows[0]["Impressions"] == 42


def test_value_normalization_handles_jalali_us_dates_and_percent(tmp_path):
    path = tmp_path / "dates.csv"
    path.write_text(
        "jalali,us_date,us_timestamp,rate,units,spend\n"
        '1404/01/15,03/04/2025,03/04/2025 11:45 PM,12%,"1,200","$1,234.50"\n',
        encoding="utf-8",
    )

    parsed = importers.parse_attachment(
        _attachment(path),
        source_format=ImportFormat.CSV,
        has_header=True,
        delimiter=",",
    )
    row = parsed.rows[0]

    assert row["jalali"] == "2025-04-04"
    assert row["us_date"] == "2025-03-04"
    assert row["us_timestamp"] == "2025-03-04T23:45:00"
    assert row["rate"] == 0.12
    assert row["units"] == 1200
    assert row["spend"] == 1234.5


def test_infer_columns_includes_source_name_nullable_and_samples():
    rows = [
        {"mixed": "1", "score": "1,200", "channel": "Search"},
        {"mixed": "abc", "score": "1300", "channel": None},
    ]

    inferred = importers.infer_columns(
        rows,
        max_columns=20,
        source_columns={"mixed": "Mixed", "score": "Score", "channel": "Channel"},
    )
    by_name = {item["name"]: item for item in inferred}

    assert by_name["mixed"]["data_type"] == TableDataType.TEXT.value
    assert by_name["score"]["data_type"] == TableDataType.INTEGER.value
    assert by_name["score"]["source_name"] == "Score"
    assert by_name["channel"]["nullable"] is True
    assert isinstance(by_name["score"]["sample_values"], list)
    assert "confidence" in by_name["score"]


def test_validate_import_rows_partial_success_and_errors():
    rows = [
        {
            "campaign": "Spring",
            "impressions": "1,200",
            "ctr": "12%",
            "event_date": "1404/01/15",
        },
        {
            "campaign": "Broken",
            "impressions": "oops",
            "ctr": "0.5",
            "event_date": "03/04/2025",
        },
    ]
    columns = [
        ReferenceTableColumnInput(name="campaign", data_type=TableDataType.TEXT, nullable=False),
        ReferenceTableColumnInput(name="impressions", data_type=TableDataType.INTEGER, nullable=False),
        ReferenceTableColumnInput(name="ctr", data_type=TableDataType.FLOAT, nullable=True),
        ReferenceTableColumnInput(name="event_date", data_type=TableDataType.DATE, nullable=True),
    ]

    normalized_rows, errors = importers.validate_import_rows(
        rows,
        columns=columns,
        max_rows=10,
        max_cell_length=200,
    )

    assert len(normalized_rows) == 1
    assert normalized_rows[0]["impressions"] == 1200
    assert normalized_rows[0]["ctr"] == 0.12
    assert normalized_rows[0]["event_date"] == "2025-04-04"
    assert len(errors) == 1
    assert errors[0]["row"] == 2
