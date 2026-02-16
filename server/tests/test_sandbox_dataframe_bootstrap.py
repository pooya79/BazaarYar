from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.features.agent.sandbox.dataframe_bootstrap import (
    SANDBOX_DATAFRAME_BOOTSTRAP_CODE,
)

pd = pytest.importorskip("pandas")


def _load_dataframe_function(input_dir: Path):
    globals_map = {
        "__name__": "__sandbox_bootstrap_test__",
        "INPUT_DIR": input_dir,
    }
    exec(SANDBOX_DATAFRAME_BOOTSTRAP_CODE, globals_map, globals_map)
    return globals_map["load_dataframe"]


def test_bootstrap_loads_utf8_bom_csv(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "bom.csv").write_text("city,score\nTehran,91\n", encoding="utf-8-sig")

    load_dataframe = _load_dataframe_function(input_dir)
    df = load_dataframe("bom.csv")

    assert list(df.columns) == ["city", "score"]
    assert df.iloc[0]["city"] == "Tehran"
    assert int(df.iloc[0]["score"]) == 91


def test_bootstrap_uses_encoding_fallback_for_latin1_csv(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "latin.csv").write_text("name\nJalapeño\n", encoding="latin-1")

    load_dataframe = _load_dataframe_function(input_dir)
    df = load_dataframe("latin.csv")

    assert df.iloc[0]["name"] == "Jalapeño"


def test_bootstrap_loads_json_and_jsonl(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "rows.json").write_text(
        json.dumps([{"campaign": "A", "spend": 10}, {"campaign": "B", "spend": 20}]),
        encoding="utf-8",
    )
    (input_dir / "rows.jsonl").write_text(
        '{"campaign":"C","spend":30}\n{"campaign":"D","spend":40}\n',
        encoding="utf-8",
    )

    load_dataframe = _load_dataframe_function(input_dir)

    json_df = load_dataframe("rows.json")
    jsonl_df = load_dataframe("rows.jsonl")

    assert list(json_df["campaign"]) == ["A", "B"]
    assert list(jsonl_df["campaign"]) == ["C", "D"]


def test_bootstrap_passes_kwargs_for_text_delimited(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "pipe.txt").write_text("channel|clicks\nemail|11\nsms|7\n", encoding="utf-8")

    load_dataframe = _load_dataframe_function(input_dir)
    df = load_dataframe("pipe.txt", sep="|")

    assert list(df.columns) == ["channel", "clicks"]
    assert list(df["channel"]) == ["email", "sms"]


def test_bootstrap_handles_unknown_extension_as_delimited_when_possible(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "metrics.custom").write_text("date,value\n2026-02-01,19\n", encoding="utf-8")

    load_dataframe = _load_dataframe_function(input_dir)
    df = load_dataframe("metrics.custom")

    assert list(df.columns) == ["date", "value"]
    assert int(df.iloc[0]["value"]) == 19


def test_bootstrap_falls_back_to_text_column_for_unparseable_text(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "notes.txt").write_text(
        'first line\n"unterminated quote\nthird line\n',
        encoding="utf-8",
    )

    load_dataframe = _load_dataframe_function(input_dir)
    df = load_dataframe("notes.txt")

    assert list(df.columns) == ["text"]
    assert list(df["text"]) == ["first line", '"unterminated quote', "third line"]


def test_bootstrap_rejects_path_traversal_and_allows_absolute_under_input(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    allowed_file = input_dir / "inside.csv"
    allowed_file.write_text("x\n1\n", encoding="utf-8")

    outside_file = tmp_path / "outside.csv"
    outside_file.write_text("x\n2\n", encoding="utf-8")

    load_dataframe = _load_dataframe_function(input_dir)

    df = load_dataframe(str(allowed_file.resolve()))
    assert int(df.iloc[0]["x"]) == 1

    with pytest.raises(ValueError, match="escapes input directory"):
        load_dataframe("../outside.csv")

    with pytest.raises(ValueError, match="escapes input directory"):
        load_dataframe(str(outside_file.resolve()))
