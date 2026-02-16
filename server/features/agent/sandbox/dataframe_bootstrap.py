from __future__ import annotations

from textwrap import dedent

SANDBOX_DATAFRAME_BOOTSTRAP_MARKER = "BAZAARYAR_SANDBOX_DATAFRAME_BOOTSTRAP"

SANDBOX_DATAFRAME_BOOTSTRAP_CODE = dedent(
    """
    # BAZAARYAR_SANDBOX_DATAFRAME_BOOTSTRAP
    from pathlib import Path

    import pandas as pd

    _DATAFRAME_ENCODING_CANDIDATES = (
        "utf-8",
        "utf-8-sig",
        "latin-1",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
    )
    _DATAFRAME_EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
    _DATAFRAME_JSON_EXTENSIONS = {".json"}
    _DATAFRAME_JSON_LINES_EXTENSIONS = {".jsonl", ".ndjson"}
    _DATAFRAME_TAB_EXTENSIONS = {".tsv", ".tab"}
    _DATAFRAME_DELIMITED_EXTENSIONS = {
        ".csv",
        ".tsv",
        ".tab",
        ".txt",
        ".text",
        ".dat",
        ".log",
        ".string",
    }
    _DATAFRAME_TEXT_FALLBACK_EXTENSIONS = {".txt", ".text", ".dat", ".log", ".string"}


    def _resolve_dataframe_path(path: str) -> Path:
        if not isinstance(path, str):
            raise TypeError("path must be a string")

        clean_path = path.strip()
        if not clean_path:
            raise ValueError("path is required")

        base_dir = Path(INPUT_DIR).resolve()
        requested = Path(clean_path)
        if requested.is_absolute():
            resolved = requested.resolve()
        else:
            resolved = (base_dir / requested).resolve()

        if resolved != base_dir and base_dir not in resolved.parents:
            raise ValueError("File path escapes input directory")

        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Input file '{clean_path}' does not exist")
        return resolved


    def _encoding_candidates(file_path: Path, *, explicit_encoding: str | None) -> list[str]:
        if explicit_encoding:
            return [explicit_encoding]

        try:
            with file_path.open("rb") as stream:
                prefix = stream.read(4)
        except OSError:
            prefix = b""

        candidates = list(_DATAFRAME_ENCODING_CANDIDATES)
        if prefix.startswith(b"\\xef\\xbb\\xbf"):
            candidates.insert(0, "utf-8-sig")
        elif prefix.startswith((b"\\xff\\xfe", b"\\xfe\\xff")):
            candidates = [
                "utf-16",
                "utf-16-le",
                "utf-16-be",
                *[
                    item
                    for item in candidates
                    if item not in {"utf-16", "utf-16-le", "utf-16-be"}
                ],
            ]

        deduped: list[str] = []
        for item in candidates:
            if item and item not in deduped:
                deduped.append(item)
        return deduped


    def _read_with_encoding_fallback(file_path: Path, *, reader, kwargs: dict):
        explicit_encoding = kwargs.get("encoding")
        if isinstance(explicit_encoding, str):
            explicit_encoding = explicit_encoding.strip() or None
        else:
            explicit_encoding = None

        candidates = _encoding_candidates(file_path, explicit_encoding=explicit_encoding)
        last_error: Exception | None = None
        for encoding in candidates:
            attempt_kwargs = dict(kwargs)
            if "encoding" not in attempt_kwargs:
                attempt_kwargs["encoding"] = encoding
            try:
                return reader(file_path, attempt_kwargs)
            except (UnicodeDecodeError, UnicodeError) as exc:
                last_error = exc
                if explicit_encoding is not None:
                    raise
                continue
            except Exception:
                raise

        if last_error is not None:
            raise last_error
        raise ValueError("No available encoding candidates.")


    def _read_delimited(file_path: Path, *, kwargs: dict, default_tab: bool) -> pd.DataFrame:
        read_kwargs = dict(kwargs)
        if default_tab and "sep" not in read_kwargs and "delimiter" not in read_kwargs:
            read_kwargs["sep"] = "\\t"

        return _read_with_encoding_fallback(
            file_path,
            kwargs=read_kwargs,
            reader=lambda path, options: pd.read_csv(path, **options),
        )


    def _read_json_file(file_path: Path, *, kwargs: dict, default_lines: bool) -> pd.DataFrame:
        read_kwargs = dict(kwargs)
        if default_lines and "lines" not in read_kwargs:
            read_kwargs["lines"] = True

        return _read_with_encoding_fallback(
            file_path,
            kwargs=read_kwargs,
            reader=lambda path, options: pd.read_json(path, **options),
        )


    def _read_text_lines(file_path: Path, *, kwargs: dict) -> pd.DataFrame:
        explicit_encoding = kwargs.get("encoding")
        if isinstance(explicit_encoding, str):
            explicit_encoding = explicit_encoding.strip() or None
        else:
            explicit_encoding = None
        errors_value = kwargs.get("encoding_errors", "strict")
        text_errors = str(errors_value or "strict")

        last_error: Exception | None = None
        for encoding in _encoding_candidates(file_path, explicit_encoding=explicit_encoding):
            try:
                with file_path.open("r", encoding=encoding, errors=text_errors) as stream:
                    lines = stream.read().splitlines()
                return pd.DataFrame({"text": lines})
            except (UnicodeDecodeError, UnicodeError) as exc:
                last_error = exc
                if explicit_encoding is not None:
                    raise
                continue

        if last_error is not None:
            raise last_error
        return pd.DataFrame({"text": []})


    def load_dataframe(path: str, **kwargs) -> pd.DataFrame:
        file_path = _resolve_dataframe_path(path)
        suffix = file_path.suffix.lower()

        if suffix in _DATAFRAME_EXCEL_EXTENSIONS:
            return pd.read_excel(file_path, **kwargs)

        if suffix in _DATAFRAME_JSON_EXTENSIONS:
            return _read_json_file(file_path, kwargs=kwargs, default_lines=False)

        if suffix in _DATAFRAME_JSON_LINES_EXTENSIONS:
            return _read_json_file(file_path, kwargs=kwargs, default_lines=True)

        if suffix in _DATAFRAME_DELIMITED_EXTENSIONS:
            try:
                return _read_delimited(
                    file_path,
                    kwargs=kwargs,
                    default_tab=suffix in _DATAFRAME_TAB_EXTENSIONS,
                )
            except Exception:
                if suffix in _DATAFRAME_TEXT_FALLBACK_EXTENSIONS:
                    return _read_text_lines(file_path, kwargs=kwargs)
                raise

        try:
            return _read_delimited(file_path, kwargs=kwargs, default_tab=False)
        except Exception:
            return _read_text_lines(file_path, kwargs=kwargs)
    """
).strip()

__all__ = [
    "SANDBOX_DATAFRAME_BOOTSTRAP_CODE",
    "SANDBOX_DATAFRAME_BOOTSTRAP_MARKER",
]
