"""从 contract.yaml 解析 schema 并对实例做子集校验（供契约测试复用）。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "spec" / "contract.yaml"

_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$",
)


def load_contract() -> dict[str, Any]:
    import yaml

    assert CONTRACT_PATH.is_file(), f"missing contract file: {CONTRACT_PATH}"
    data = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "contract.yaml root must be a mapping"
    return data


def schema_by_name(spec: Mapping[str, Any], name: str) -> dict[str, Any]:
    return spec["components"]["schemas"][name]  # type: ignore[no-any-return]


def _resolve_ref(spec: Mapping[str, Any], ref: str) -> dict[str, Any]:
    assert ref.startswith("#/components/schemas/"), f"unsupported ref: {ref}"
    key = ref.rsplit("/", 1)[-1]
    return schema_by_name(spec, key)


def _validate_format(value: str, fmt: str) -> str | None:
    if fmt == "date-time":
        return None if _DT_RE.match(value) else "expected ISO-8601 date-time string"
    return None


def validate_instance(  # noqa: PLR0911
    instance: Any,
    schema: Any,
    spec: Mapping[str, Any],
    *,
    path: str = "$",
) -> list[str]:
    """返回错误列表；空表示通过（相对 OpenAPI schema 子集）。"""
    if not isinstance(schema, dict):
        return [f"{path}: schema fragment must be an object"]

    if schema.get("nullable") is True and instance is None:
        return []

    if instance is None:
        return [f"{path}: value is null but null is not allowed here"]

    if "$ref" in schema:
        return validate_instance(instance, _resolve_ref(spec, schema["$ref"]), spec, path=path)

    if "allOf" in schema:
        errs: list[str] = []
        for i, part in enumerate(schema["allOf"]):
            errs.extend(
                validate_instance(instance, part, spec, path=f"{path}.allOf[{i}]"),
            )
        return errs

    typ = schema.get("type")

    if typ == "object":
        if not isinstance(instance, dict):
            return [f"{path}: expected object, got {type(instance).__name__}"]
        errs: list[str] = []
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required property {req!r}")
        props = schema.get("properties") or {}
        for key, val in instance.items():
            if key not in props:
                continue
            errs.extend(validate_instance(val, props[key], spec, path=f"{path}.{key}"))
        return errs

    if typ == "string":
        if not isinstance(instance, str):
            return [f"{path}: expected string, got {type(instance).__name__}"]
        if "enum" in schema and instance not in schema["enum"]:
            return [f"{path}: enum violation: {instance!r} not in {schema['enum']!r}"]
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            return [f"{path}: length {len(instance)} < minLength={schema['minLength']}"]
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            return [f"{path}: length {len(instance)} > maxLength={schema['maxLength']}"]
        fmt = schema.get("format")
        if isinstance(fmt, str):
            fmt_err = _validate_format(instance, fmt)
            if fmt_err:
                return [f"{path}: {fmt_err}"]
        return []

    if typ == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: expected integer (non-bool), got {type(instance).__name__}"]
        if "enum" in schema and instance not in schema["enum"]:
            return [f"{path}: enum violation: {instance!r} not in {schema['enum']!r}"]
        if "minimum" in schema and instance < int(schema["minimum"]):
            return [f"{path}: {instance} < minimum={schema['minimum']}"]
        if "maximum" in schema and instance > int(schema["maximum"]):
            return [f"{path}: {instance} > maximum={schema['maximum']}"]
        return []

    if typ == "array":
        if not isinstance(instance, list):
            return [f"{path}: expected array, got {type(instance).__name__}"]
        items = schema.get("items")
        if not isinstance(items, dict):
            return [f"{path}: array items schema missing or invalid"]
        errs: list[str] = []
        for i, elem in enumerate(instance):
            errs.extend(validate_instance(elem, items, spec, path=f"{path}[{i}]"))
        return errs

    if typ == "boolean":
        if not isinstance(instance, bool):
            return [f"{path}: expected boolean, got {type(instance).__name__}"]
        return []

    if typ == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: expected number, got {type(instance).__name__}"]
        return []

    return [f"{path}: unsupported schema.type={typ!r}"]


def assert_contract_instance(
    spec: Mapping[str, Any],
    schema_name: str,
    instance: Any,
    *,
    expect_valid: bool,
    error_substrings: tuple[str, ...] = (),
) -> None:
    """expect_valid=False 时建议提供 error_substrings，避免“任意一条假错”即通过。"""
    sch = schema_by_name(spec, schema_name)
    errors = validate_instance(instance, sch, spec)
    joined = "\n".join(errors)
    if expect_valid:
        assert errors == [], f"{schema_name}: expected valid instance, errors: {errors}"
        return
    assert errors, f"{schema_name}: expected invalid instance to fail validation: {instance!r}"
    for frag in error_substrings:
        assert frag in joined, (
            f"{schema_name}: expected error fragment {frag!r} in:\n{joined}"
        )
