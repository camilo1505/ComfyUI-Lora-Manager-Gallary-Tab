"""Tests for the locale JSON git merge driver (scripts/merge_locales_driver.py).

The driver is a 3-way key-level merge used by git (via ``.gitattributes`` +
``merge.locales.driver``) so two branches adding keys to the same locale do
not produce whole-file content conflicts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
DRIVER = ROOT_DIR / "scripts" / "merge_locales_driver.py"

INDENT = 4
SEPARATORS = (",", ": ")


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, indent=INDENT, ensure_ascii=False, separators=SEPARATORS), encoding="utf-8")
    return path


def run_driver(tmp_path: Path, base: dict, ours: dict, theirs: dict) -> dict:
    base_path = _write(tmp_path, "base.json", base)
    ours_path = _write(tmp_path, "ours.json", ours)
    theirs_path = _write(tmp_path, "theirs.json", theirs)
    result = subprocess.run(
        [sys.executable, str(DRIVER), str(base_path), str(ours_path), str(theirs_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"driver failed: {result.stderr}"
    return json.loads(ours_path.read_text(encoding="utf-8"))


def test_union_of_keys_from_both_sides(tmp_path) -> None:
    result = run_driver(
        tmp_path,
        {"a": "1", "shared": "base"},
        {"a": "1", "shared": "base", "ours_key": "ours"},
        {"a": "1", "shared": "base", "theirs_key": "theirs"},
    )
    assert result["ours_key"] == "ours"
    assert result["theirs_key"] == "theirs"


def test_shared_key_changed_by_both_prefers_theirs(tmp_path) -> None:
    result = run_driver(
        tmp_path,
        {"msg": "base"},
        {"msg": "ours change"},
        {"msg": "theirs change"},
    )
    assert result["msg"] == "theirs change"


def test_shared_key_changed_only_by_ours_keeps_ours(tmp_path) -> None:
    result = run_driver(
        tmp_path,
        {"msg": "base"},
        {"msg": "ours change"},
        {"msg": "base"},
    )
    assert result["msg"] == "ours change"


def test_shared_key_changed_only_by_theirs_takes_theirs(tmp_path) -> None:
    result = run_driver(
        tmp_path,
        {"msg": "base"},
        {"msg": "base"},
        {"msg": "theirs change"},
    )
    assert result["msg"] == "theirs change"


def test_nested_objects_merge_recursively(tmp_path) -> None:
    result = run_driver(
        tmp_path,
        {"menu": {"a": "1", "shared": "base"}, "top": "keep"},
        {"menu": {"a": "1", "shared": "base", "ours_nested": "x"}, "top": "keep"},
        {"menu": {"a": "1", "shared": "theirs", "theirs_nested": "y"}, "top": "keep"},
    )
    assert result["menu"]["ours_nested"] == "x"
    assert result["menu"]["theirs_nested"] == "y"
    assert result["menu"]["shared"] == "theirs"


def test_output_uses_canonical_format(tmp_path) -> None:
    base_path = _write(tmp_path, "base.json", {"a": "1"})
    ours_path = _write(tmp_path, "ours.json", {"a": "1", "b": "2"})
    theirs_path = _write(tmp_path, "theirs.json", {"a": "1"})
    result = subprocess.run(
        [sys.executable, str(DRIVER), str(base_path), str(ours_path), str(theirs_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    expected = json.dumps({"a": "1", "b": "2"}, indent=INDENT, ensure_ascii=False, separators=SEPARATORS) + "\n"
    assert ours_path.read_text(encoding="utf-8") == expected


def test_invalid_json_returns_error(tmp_path) -> None:
    base_path = _write(tmp_path, "base.json", {"a": "1"})
    ours_path = tmp_path / "ours.json"
    ours_path.write_text("{not valid json", encoding="utf-8")
    theirs_path = _write(tmp_path, "theirs.json", {"a": "1"})
    result = subprocess.run(
        [sys.executable, str(DRIVER), str(base_path), str(ours_path), str(theirs_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1