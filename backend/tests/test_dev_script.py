"""Tests for project-readiness checks in scripts/dev.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _load_dev_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "dev.py"
    spec = importlib.util.spec_from_file_location("asia_dev_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DEV = _load_dev_module()


@pytest.mark.parametrize(
    ("version", "supported"),
    [
        ("v20.18.1", False),
        ("v20.19.0", True),
        ("v20.20.0", True),
        ("v21.7.3", False),
        ("v22.11.0", False),
        ("v22.12.0", True),
        ("v23.0.0", True),
        ("v25.8.1", True),
        ("not-a-version", False),
    ],
)
def test_node_version_matches_vite_engine_range(
    version: str,
    supported: bool,
) -> None:
    assert DEV._node_version_supported(version) is supported


def test_frontend_scripts_are_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "package.json"
    manifest_path.write_text(
        json.dumps(
            {
                "engines": {
                    "node": DEV.SUPPORTED_NODE_RANGE,
                },
                "scripts": {"typecheck": "tsc -b"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(DEV, "FRONTEND_PKG", manifest_path)

    assert DEV._check_frontend_scripts() is False

    manifest_path.write_text(
        json.dumps(
            {
                "engines": {
                    "node": DEV.SUPPORTED_NODE_RANGE,
                },
                "scripts": {
                    "typecheck": "tsc -b",
                    "build": "tsc -b && vite build",
                }
            }
        ),
        encoding="utf-8",
    )
    assert DEV._check_frontend_scripts() is True


def test_frontend_manifest_must_declare_supported_node_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "package.json"
    manifest_path.write_text(
        json.dumps(
            {
                "engines": {"node": ">=18"},
                "scripts": {
                    "typecheck": "tsc -b",
                    "build": "tsc -b && vite build",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(DEV, "FRONTEND_PKG", manifest_path)

    assert DEV._check_frontend_scripts() is False


def test_missing_frontend_dependencies_fail_with_install_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        DEV,
        "FRONTEND_NODE_MODULES",
        tmp_path / "node_modules",
    )

    assert DEV._check_frontend_dependencies() is False
    assert "npm ci" in capsys.readouterr().out


def test_runtime_directory_must_be_writable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_dir = tmp_path / "var"
    monkeypatch.setattr(DEV, "RUNTIME_DIR", runtime_dir)

    assert DEV._check_runtime_writable() is True
    assert runtime_dir.is_dir()
    assert tuple(runtime_dir.iterdir()) == ()
