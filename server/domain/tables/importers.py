from __future__ import annotations

import io
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd

from server.agents.attachments import resolve_storage_path
from server.db.models import Attachment

from .errors import ImportFormatError
from .schema import validate_row_values
from .types import ImportFormat, ReferenceTableColumnInput, TableDataType

_HEADER_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_]+")
_CURRENCY_CHARS_RE = re.compile(r"[$€£¥₹₽₩₪₺₫]")
_JALALI_RE = re.compile(
    r"^(?P<year>1[34]\d{2})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})"
    r"(?:(?:\s+|T)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?)?$"
)
_TIMESTAMP_TOKEN_RE = re.compile(r"[:T]|[ ]\d{1,2}:\d{2}")
_PANDAS_UNNAMED_HEADER_RE = re.compile(r"^Unnamed:\s*\d+$")
_PANDAS_DUPLICATE_SUFFIX_RE = re.compile(r"^(?P<base>.+)\.(?P<index>\d+)$")
_MAX_INFERENCE_SAMPLE = 250
_SAMPLE_VALUE_COUNT = 3


@dataclass
class ParsedImportData:
    source_format: ImportFormat
    rows: list[dict[str, Any]]
    dataset_name_suggestion: str
    source_columns: dict[str, str]


def _normalize_header(value: str, *, fallback_index: int) -> str:
    candidate = _HEADER_TOKEN_RE.sub("_", value.strip()).strip("_")
    if not candidate:
        candidate = f"column_{fallback_index}"
    if not re.match(r"^[a-zA-Z_]", candidate):
        candidate = f"column_{candidate}"
    return candidate[:63]


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    output: list[str] = []
    for raw_header in headers:
        header = raw_header[:63]
        count = seen.get(header, 0)
        while True:
            if count == 0:
                candidate = header
            else:
                suffix = f"_{count + 1}"
                base_limit = max(1, 63 - len(suffix))
                candidate = f"{header[:base_limit]}{suffix}"
            if candidate not in used:
                break
            count += 1
        seen[header] = count + 1
        used.add(candidate)
        output.append(candidate)
    return output


def _suggest_dataset_name(filename: str | None) -> str:
    stem = Path(filename or "").stem.strip()
    if not stem:
        return "dataset"
    candidate = _normalize_header(stem, fallback_index=1)
    return candidate or "dataset"


def _load_csv_dataframe(
    payload: bytes,
    *,
    has_header: bool,
    delimiter: str | None,
) -> pd.DataFrame:
    kwargs: dict[str, Any] = {
        "header": 0 if has_header else None,
        "dtype": object,
        "keep_default_na": False,
    }
    if delimiter is None:
        kwargs["sep"] = None
        kwargs["engine"] = "python"
    else:
        kwargs["sep"] = delimiter
        kwargs["engine"] = "python"

    try:
        return pd.read_csv(io.BytesIO(payload), **kwargs)
    except Exception as exc:  # pragma: no cover - defensive wrappers
        raise ImportFormatError(f"Could not parse CSV file: {exc}") from exc


def _load_json_dataframe(payload: bytes) -> pd.DataFrame:
    try:
        parsed = json.loads(payload.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise ImportFormatError(f"Could not parse JSON file: {exc}") from exc

    if isinstance(parsed, dict) and isinstance(parsed.get("rows"), list):
        parsed = parsed["rows"]

    if not isinstance(parsed, list):
        raise ImportFormatError("JSON import expects a list of objects or {\"rows\": [...]}.")

    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise ImportFormatError(f"JSON row {index} is not an object.")

    try:
        return pd.json_normalize(parsed, sep=".")
    except Exception as exc:
        raise ImportFormatError(f"Could not normalize JSON rows: {exc}") from exc


def _load_xlsx_dataframe(payload: bytes, *, has_header: bool) -> pd.DataFrame:
    kwargs: dict[str, Any] = {
        "sheet_name": 0,
        "header": 0 if has_header else None,
        "dtype": object,
        "engine": "openpyxl",
        "keep_default_na": False,
    }
    try:
        return pd.read_excel(io.BytesIO(payload), **kwargs)
    except ImportError as exc:
        raise ImportFormatError(
            "XLSX import requires openpyxl and pandas. Install dependencies and retry."
        ) from exc
    except Exception as exc:
        raise ImportFormatError(f"Could not parse XLSX file: {exc}") from exc


def _coerce_jalali_temporal(text: str) -> str | None:
    matched = _JALALI_RE.fullmatch(text)
    if not matched:
        return None
    try:
        import jdatetime

        gregorian = jdatetime.date(
            int(matched.group("year")),
            int(matched.group("month")),
            int(matched.group("day")),
        ).togregorian()
        if matched.group("hour") is None:
            return gregorian.isoformat()
        converted = datetime.combine(
            gregorian,
            time(
                hour=int(matched.group("hour")),
                minute=int(matched.group("minute")),
                second=int(matched.group("second") or 0),
            ),
        )
        return converted.isoformat()
    except Exception:
        return None


def _coerce_temporal_value(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    jalali = _coerce_jalali_temporal(text)
    if jalali is not None:
        return jalali

    normalized = text.replace("Z", "+00:00")
    try:
        parsed_ts = datetime.fromisoformat(normalized)
        return parsed_ts.isoformat()
    except Exception:
        pass
    try:
        parsed_date = date.fromisoformat(normalized)
        return parsed_date.isoformat()
    except Exception:
        pass

    date_formats = [
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m/%d/%y",
        "%m-%d-%y",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except Exception:
            continue

    timestamp_formats = [
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m-%d-%Y %H:%M",
        "%m-%d-%Y %H:%M:%S",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%m-%d-%Y %I:%M %p",
        "%m-%d-%Y %I:%M:%S %p",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in timestamp_formats:
        try:
            return datetime.strptime(text, fmt).isoformat()
        except Exception:
            continue

    return None


def _coerce_boolean_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "y", "on"}:
        return True
    if lowered in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _parse_numeric_string(raw: str) -> float | int | None:
    text = raw.strip()
    if not text:
        return None

    is_negative = text.startswith("(") and text.endswith(")")
    if is_negative:
        text = text[1:-1].strip()

    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1].strip()

    text = _CURRENCY_CHARS_RE.sub("", text)
    text = text.replace(",", "").replace(" ", "")

    if not text or text in {".", "+", "-", "+.", "-."}:
        return None

    try:
        number = float(text)
    except Exception:
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    if is_negative:
        number = -number
    if is_percent:
        number /= 100

    if not is_percent and number.is_integer():
        return int(number)
    return number


def _coerce_integer_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        parsed = _parse_numeric_string(value)
        if isinstance(parsed, int):
            return parsed
        if isinstance(parsed, float) and parsed.is_integer():
            return int(parsed)
    return None


def _coerce_float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    if isinstance(value, str):
        parsed = _parse_numeric_string(value)
        if parsed is None:
            return None
        return float(parsed)
    return None


def _coerce_json_value(value: Any) -> dict[str, Any] | list[Any] | None:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if not (text.startswith("{") or text.startswith("[")):
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return None


def _is_nullish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (dict, list, tuple)):
        return False
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _coerce_python_scalar(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return value
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _canonicalize_value(value: Any) -> Any:
    value = _coerce_python_scalar(value)
    if _is_nullish(value):
        return None

    if isinstance(value, dict):
        return {str(key): _canonicalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_value(item) for item in value]

    temporal = _coerce_temporal_value(value)
    if temporal is not None:
        return temporal

    if isinstance(value, str):
        boolean = _coerce_boolean_value(value)
        if boolean is not None:
            return boolean
        numeric = _parse_numeric_string(value)
        if numeric is not None:
            return numeric
        json_value = _coerce_json_value(value)
        if json_value is not None:
            return _canonicalize_value(json_value)
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return value

    return str(value)


def _dataframe_to_rows(
    frame: pd.DataFrame,
    *,
    has_header: bool,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if frame is None:
        return [], {}

    if has_header:
        source_headers: list[str] = []
        for item in frame.columns:
            raw_header = "" if item is None else str(item).strip()
            if _PANDAS_UNNAMED_HEADER_RE.fullmatch(raw_header):
                source_headers.append("")
                continue
            matched = _PANDAS_DUPLICATE_SUFFIX_RE.fullmatch(raw_header)
            if matched is not None:
                source_headers.append(matched.group("base"))
                continue
            source_headers.append(raw_header)
        normalized_headers = _dedupe_headers(
            [
                _normalize_header(header, fallback_index=index + 1)
                for index, header in enumerate(source_headers)
            ]
        )
    else:
        normalized_headers = [f"column_{index + 1}" for index in range(len(frame.columns))]
        source_headers = normalized_headers[:]

    source_columns = {
        normalized: (source.strip() if source.strip() else normalized)
        for normalized, source in zip(normalized_headers, source_headers)
    }

    mapped = frame.copy()
    mapped.columns = normalized_headers

    rows: list[dict[str, Any]] = []
    for item in mapped.to_dict(orient="records"):
        rows.append({key: _canonicalize_value(value) for key, value in item.items()})
    return rows, source_columns


def detect_format(
    *,
    source_format: ImportFormat | None,
    filename: str | None,
) -> ImportFormat:
    if source_format is not None:
        return source_format

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".csv":
        return ImportFormat.CSV
    if suffix == ".json":
        return ImportFormat.JSON
    if suffix in {".xlsx", ".xlsm"}:
        return ImportFormat.XLSX

    raise ImportFormatError("Could not infer import format. Provide source_format explicitly.")


def parse_attachment(
    attachment: Attachment,
    *,
    source_format: ImportFormat | None,
    has_header: bool,
    delimiter: str | None,
) -> ParsedImportData:
    path = resolve_storage_path(attachment.storage_path)
    if not path.exists():
        raise ImportFormatError(f"Attachment file '{attachment.id}' is missing on disk.")

    resolved_format = detect_format(source_format=source_format, filename=attachment.filename)
    payload = path.read_bytes()
    dataset_name_suggestion = _suggest_dataset_name(attachment.filename)

    if resolved_format == ImportFormat.CSV:
        frame = _load_csv_dataframe(payload, has_header=has_header, delimiter=delimiter)
        rows, source_columns = _dataframe_to_rows(frame, has_header=has_header)
    elif resolved_format == ImportFormat.JSON:
        frame = _load_json_dataframe(payload)
        rows, source_columns = _dataframe_to_rows(frame, has_header=True)
    elif resolved_format == ImportFormat.XLSX:
        frame = _load_xlsx_dataframe(payload, has_header=has_header)
        rows, source_columns = _dataframe_to_rows(frame, has_header=has_header)
    else:  # pragma: no cover - enum guard
        raise ImportFormatError(f"Unsupported format '{resolved_format}'.")

    return ParsedImportData(
        source_format=resolved_format,
        rows=rows,
        dataset_name_suggestion=dataset_name_suggestion,
        source_columns=source_columns,
    )


def _coerce_temporal_kind(value: Any) -> tuple[str, str] | None:
    converted = _coerce_temporal_value(value)
    if converted is None:
        return None
    if _TIMESTAMP_TOKEN_RE.search(converted):
        return ("timestamp", converted)
    return ("date", converted)


def _ratio(values: list[Any], parser) -> float:
    if not values:
        return 0.0
    successes = 0
    for value in values:
        if parser(value):
            successes += 1
    return successes / len(values)


def _infer_type(values: list[Any]) -> tuple[TableDataType, float, list[Any], bool]:
    sample = [_canonicalize_value(item) for item in values[:_MAX_INFERENCE_SAMPLE]]
    non_null = [item for item in sample if not _is_nullish(item)]
    nullable = len(non_null) < len(sample)
    if not non_null:
        return TableDataType.TEXT, 0.4, [], True

    bool_ratio = _ratio(non_null, lambda item: _coerce_boolean_value(item) is not None)
    int_ratio = _ratio(non_null, lambda item: _coerce_integer_value(item) is not None)
    float_ratio = _ratio(non_null, lambda item: _coerce_float_value(item) is not None)
    date_ratio = _ratio(
        non_null,
        lambda item: (candidate := _coerce_temporal_kind(item)) is not None and candidate[0] == "date",
    )
    timestamp_ratio = _ratio(
        non_null,
        lambda item: (candidate := _coerce_temporal_kind(item)) is not None and candidate[0] == "timestamp",
    )
    json_ratio = _ratio(non_null, lambda item: _coerce_json_value(item) is not None)

    ratios: list[tuple[TableDataType, float]] = [
        (TableDataType.BOOLEAN, bool_ratio),
        (TableDataType.INTEGER, int_ratio),
        (TableDataType.FLOAT, float_ratio),
        (TableDataType.TIMESTAMP, timestamp_ratio),
        (TableDataType.DATE, date_ratio),
        (TableDataType.JSON, json_ratio),
    ]
    inferred_type, best_ratio = max(ratios, key=lambda item: item[1])

    sample_values: list[Any] = []
    for value in non_null:
        sample_values.append(value)
        if len(sample_values) >= _SAMPLE_VALUE_COUNT:
            break

    if best_ratio < 0.7:
        return TableDataType.TEXT, 0.6, sample_values, nullable
    return inferred_type, round(best_ratio, 3), sample_values, nullable


def infer_columns(
    rows: list[dict[str, Any]],
    *,
    max_columns: int,
    source_columns: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    all_keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in all_keys:
                all_keys.append(key)

    if len(all_keys) > max_columns:
        raise ImportFormatError(f"Too many columns in source file. Maximum is {max_columns}.")

    inferred: list[dict[str, Any]] = []
    for key in all_keys:
        sample = [row.get(key) for row in rows[:_MAX_INFERENCE_SAMPLE]]
        inferred_type, confidence, sample_values, nullable = _infer_type(sample)
        inferred.append(
            {
                "name": key,
                "source_name": (source_columns or {}).get(key, key),
                "data_type": inferred_type.value,
                "confidence": confidence,
                "nullable": nullable,
                "sample_values": sample_values,
            }
        )
    return inferred


def _preprocess_for_column(value: Any, data_type: TableDataType) -> Any:
    if value is None:
        return None

    if data_type == TableDataType.INTEGER:
        converted = _coerce_integer_value(value)
        return value if converted is None else converted

    if data_type == TableDataType.FLOAT:
        converted = _coerce_float_value(value)
        return value if converted is None else converted

    if data_type == TableDataType.BOOLEAN:
        converted = _coerce_boolean_value(value)
        return value if converted is None else converted

    if data_type == TableDataType.DATE:
        converted = _coerce_temporal_value(value)
        if converted is None:
            return value
        if _TIMESTAMP_TOKEN_RE.search(converted):
            try:
                return datetime.fromisoformat(converted.replace("Z", "+00:00")).date().isoformat()
            except Exception:
                return converted
        return converted

    if data_type == TableDataType.TIMESTAMP:
        converted = _coerce_temporal_value(value)
        return value if converted is None else converted

    if data_type == TableDataType.JSON:
        converted = _coerce_json_value(value)
        if converted is not None:
            return converted
        return value

    if data_type == TableDataType.TEXT and isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None

    return value


def validate_import_rows(
    rows: list[dict[str, Any]],
    *,
    columns: list[ReferenceTableColumnInput],
    max_rows: int,
    max_cell_length: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(rows) > max_rows:
        raise ImportFormatError(f"Import row count exceeds maximum of {max_rows}.")

    normalized_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    column_map = {column.name: column for column in columns}

    for index, row in enumerate(rows, start=1):
        prepared: dict[str, Any] = {}
        for key, value in row.items():
            column = column_map.get(key)
            if column is None:
                prepared[key] = value
                continue
            prepared[key] = _preprocess_for_column(value, column.data_type)

        try:
            normalized = validate_row_values(
                prepared,
                columns=columns,
                max_cell_length=max_cell_length,
            )
            normalized_rows.append(normalized)
        except Exception as exc:
            if hasattr(exc, "errors"):
                errors.append(
                    {
                        "row": index,
                        "error": str(exc),
                        "details": getattr(exc, "errors", []),
                    }
                )
            else:
                errors.append({"row": index, "error": str(exc)})

    return normalized_rows, errors
