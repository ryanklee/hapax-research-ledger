from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "sced-observation-v0.json"
LEDGER_PATH = ROOT / "dv-ledger.ndjson"
LATEST_PATH = ROOT / "latest.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                raise ValueError(f"{path}:{line_number}: blank lines are not valid ledger records")
            data = json.loads(stripped)
            if not isinstance(data, dict):
                raise TypeError(f"{path}:{line_number}: ledger record must be a JSON object")
            records.append(data)
    if not records:
        raise ValueError(f"{path} must contain at least one observation")
    return records


def canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    records = load_ndjson(LEDGER_PATH)
    latest = load_json(LATEST_PATH)

    failures: list[str] = []
    for label, data in [("latest.json", latest), *[(f"dv-ledger.ndjson:{i}", r) for i, r in enumerate(records, start=1)]]:
        errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
        for error in errors:
            path = ".".join(str(part) for part in error.path) or "<root>"
            failures.append(f"{label}: {path}: {error.message}")

    if canonical(latest) != canonical(records[-1]):
        failures.append("latest.json must match the final record in dv-ledger.ndjson")

    observation_ids = [record["observation_id"] for record in records]
    duplicates = sorted({item for item in observation_ids if observation_ids.count(item) > 1})
    if duplicates:
        failures.append(f"duplicate observation_id values: {', '.join(duplicates)}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"ledger validation passed: {len(records)} observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
