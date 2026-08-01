"""Validate stable route properties used by the OpportunIQ frontend."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
REQUIRED_OPERATIONS = {
    ("post", "/api/profile/manual"),
    ("post", "/api/profile/upload"),
    ("post", "/api/opportunities/search"),
    ("get", "/api/opportunities"),
    ("post", "/api/saved/{opportunity_id}"),
    ("get", "/api/deadlines/calendar"),
    ("patch", "/api/notifications/read-all"),
    ("get", "/api/notifications/scheduler/status"),
    ("post", "/api/gap-analysis/run"),
}


def _allows_string(schema: dict) -> bool:
    if schema.get("type") == "string":
        return True
    return any(option.get("type") == "string" for option in schema.get("anyOf", []))


def validate() -> tuple[int, int]:
    schema = app.openapi()
    operations: list[tuple[str, str, dict]] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                operations.append((method, path, operation))

    operation_ids = [item[2].get("operationId") for item in operations]
    if None in operation_ids or len(operation_ids) != len(set(operation_ids)):
        raise SystemExit("OpenAPI operation IDs are missing or duplicated")
    if any(not operation.get("tags") for _, _, operation in operations):
        raise SystemExit("Every HTTP operation must have at least one tag")

    actual = {(method, path) for method, path, _ in operations}
    missing = REQUIRED_OPERATIONS - actual
    if missing:
        raise SystemExit(f"Required frontend operations are missing: {sorted(missing)}")

    for _method, path, operation in operations:
        for parameter in operation.get("parameters", []):
            name = str(parameter.get("name", ""))
            if name.endswith("_id") and not _allows_string(parameter.get("schema", {})):
                raise SystemExit(f"Public ID parameter is not a string: {path} {name}")

    return len(operations), len(schema["paths"])


if __name__ == "__main__":
    operation_count, path_count = validate()
    print(
        f"OpenAPI validation OK: {operation_count} HTTP operations across "
        f"{path_count} paths"
    )
