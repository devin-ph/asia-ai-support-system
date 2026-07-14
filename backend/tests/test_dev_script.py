"""Tests for project-readiness checks in scripts/dev.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from argparse import Namespace
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

PROVIDER_ENV_EXAMPLE = """\
ASIA_RESPONSE_GENERATOR=template
ASIA_LLM_API_KEY=
ASIA_LLM_MODEL=
ASIA_LLM_TIMEOUT_SECONDS=15
"""


def _clear_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in DEV.PROVIDER_ENV_KEYS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("version", "supported"),
    [
        ("v20.18.1", False),
        ("v20.19.0", True),
        ("v20.20.0", True),
        ("v21.7.3", False),
        ("v22.11.0", False),
        ("v22.12.0", True),
        ("v22.99.0", True),
        ("v23.0.0", False),
        ("v24.0.0", False),
        ("v25.8.1", False),
        ("not-a-version", False),
    ],
)
def test_node_version_matches_vite_engine_range(
    version: str,
    supported: bool,
) -> None:
    assert DEV._node_version_supported(version) is supported


def test_default_node_version_file_selects_node_22(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version_file = tmp_path / ".nvmrc"
    monkeypatch.setattr(DEV, "NODE_VERSION_FILE", version_file)

    version_file.write_text("22\n", encoding="utf-8")
    assert DEV._check_default_node_version() is True

    version_file.write_text("25\n", encoding="utf-8")
    assert DEV._check_default_node_version() is False


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
                    "test": "vitest run",
                    "typecheck": "tsc -b",
                    "build": "tsc -b && vite build",
                    "e2e": "playwright test",
                },
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
                    "test": "vitest run",
                    "typecheck": "tsc -b",
                    "build": "tsc -b && vite build",
                    "e2e": "playwright test",
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


def test_reset_demo_copies_ticket_seed_to_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_path = tmp_path / "data" / "fixtures" / "demo_tickets.seed.json"
    runtime_dir = tmp_path / "var"
    runtime_path = runtime_dir / "demo_tickets.json"
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text("[]\n", encoding="utf-8")
    runtime_dir.mkdir()
    runtime_path.write_text(
        '[{"ticket_id": "tkt_old", "action_id": "act_old"}]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(DEV, "ROOT", tmp_path)
    monkeypatch.setattr(DEV, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(DEV, "RUNTIME_TICKETS", runtime_path)
    monkeypatch.setattr(DEV, "TICKET_SEED", seed_path)

    assert DEV.cmd_reset_demo(Namespace()) == 0

    assert runtime_path.read_text(encoding="utf-8") == "[]\n"
    assert seed_path.read_text(encoding="utf-8") == "[]\n"
    output = capsys.readouterr().out
    assert "Reset var/demo_tickets.json from data/fixtures/demo_tickets.seed.json" in output


def test_doctor_accepts_template_mode_without_local_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text(PROVIDER_ENV_EXAMPLE, encoding="utf-8")
    monkeypatch.setattr(DEV, "ENV_EXAMPLE", env_example)
    monkeypatch.setattr(DEV, "ENV_FILE", tmp_path / ".env")
    _clear_provider_environment(monkeypatch)

    assert DEV._check_env_configuration() is True


def test_doctor_requires_only_settings_for_selected_openai_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_example = tmp_path / ".env.example"
    env_file = tmp_path / ".env"
    secret = "test-placeholder-secret-value"
    env_example.write_text(PROVIDER_ENV_EXAMPLE, encoding="utf-8")
    env_file.write_text(
        f"ASIA_RESPONSE_GENERATOR=openai\nASIA_LLM_API_KEY={secret}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(DEV, "ENV_EXAMPLE", env_example)
    monkeypatch.setattr(DEV, "ENV_FILE", env_file)
    _clear_provider_environment(monkeypatch)

    assert DEV._check_env_configuration() is False
    assert "ASIA_LLM_MODEL" in capsys.readouterr().out

    env_file.write_text(
        (
            "ASIA_RESPONSE_GENERATOR=openai\n"
            f"ASIA_LLM_API_KEY={secret}\n"
            "ASIA_LLM_MODEL=gpt-5.4-mini-2026-03-17\n"
            "ASIA_LLM_TIMEOUT_SECONDS=12\n"
        ),
        encoding="utf-8",
    )
    assert DEV._check_env_configuration() is True
    assert secret not in capsys.readouterr().out


@pytest.mark.parametrize(
    "local_values",
    [
        "ASIA_RESPONSE_GENERATOR=external\n",
        "ASIA_LLM_TIMEOUT_SECONDS=0\n",
        "ASIA_LLM_TIMEOUT_SECONDS=not-a-number\n",
    ],
)
def test_doctor_rejects_unknown_provider_and_invalid_timeout(
    local_values: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_example = tmp_path / ".env.example"
    env_file = tmp_path / ".env"
    env_example.write_text(PROVIDER_ENV_EXAMPLE, encoding="utf-8")
    env_file.write_text(local_values, encoding="utf-8")
    monkeypatch.setattr(DEV, "ENV_EXAMPLE", env_example)
    monkeypatch.setattr(DEV, "ENV_FILE", env_file)
    _clear_provider_environment(monkeypatch)

    assert DEV._check_env_configuration() is False


def test_backend_environment_keeps_process_values_over_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ASIA_RESPONSE_GENERATOR=openai\nASIA_LLM_MODEL=file-model\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(DEV, "ENV_FILE", env_file)
    monkeypatch.setenv("ASIA_LLM_MODEL", "process-model")

    environment = DEV._backend_environment()

    assert environment["ASIA_RESPONSE_GENERATOR"] == "openai"
    assert environment["ASIA_LLM_MODEL"] == "process-model"


def test_runtime_hygiene_rejects_fixture_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_path = tmp_path / "demo_tickets.seed.json"
    seed_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(DEV, "TICKET_SEED", seed_path)

    def git_result(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if command[1] == "ls-files":
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[1] == "check-ignore":
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[1] == "status":
            return subprocess.CompletedProcess(
                command,
                0,
                " M data/fixtures/demo_orders.json\n",
                "",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(DEV.subprocess, "run", git_result)

    assert DEV._check_runtime_hygiene() is False


def test_requirement_lock_accepts_only_exact_pins(tmp_path: Path) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text(
        "# generated\nfastapi==0.139.0\npydantic-core==2.46.4\n",
        encoding="utf-8",
    )

    assert DEV._load_requirement_pins(lock_path) == {
        "fastapi": "0.139.0",
        "pydantic-core": "2.46.4",
    }

    lock_path.write_text("fastapi>=0.115,<1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-pinned"):
        DEV._load_requirement_pins(lock_path)


def test_backend_dependency_lock_detects_installed_version_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "requirements.txt"
    lock_path.write_text("fastapi==0.139.0\n", encoding="utf-8")
    monkeypatch.setattr(DEV, "BACKEND_REQUIREMENTS_LOCK", lock_path)
    monkeypatch.setattr(
        DEV.importlib.metadata,
        "version",
        lambda _name: "0.138.0",
    )

    assert DEV._check_backend_dependency_lock() is False


def test_pip_consistency_uses_active_interpreter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def pip_check(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert command == [DEV.sys.executable, "-m", "pip", "check"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(DEV.subprocess, "run", pip_check)

    assert DEV._check_pip_consistency() is True


def test_eval_command_forwards_versioned_suite_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def run_evaluation(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(DEV.subprocess, "run", run_evaluation)

    assert DEV.cmd_eval(Namespace(suite="v0.2", json=True)) == 0
    assert calls == [
        (
            [
                DEV.sys.executable,
                str(DEV.EVALUATION_SCRIPT),
                "--suite",
                "v0.2",
                "--json",
            ],
            DEV.ROOT,
        )
    ]


def test_python_quality_gates_use_active_interpreter() -> None:
    assert DEV._python_quality_commands() == (
        (
            "Python lint",
            [
                DEV.sys.executable,
                "-m",
                "ruff",
                "check",
                "backend",
                "scripts",
            ],
        ),
        (
            "Python format",
            [
                DEV.sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "backend",
                "scripts",
            ],
        ),
    )


def test_python_security_gate_uses_active_interpreter_and_locked_requirements() -> None:
    assert DEV._python_security_commands() == (
        (
            "Python vulnerability audit",
            [
                DEV.sys.executable,
                "-m",
                "pip_audit",
                "-r",
                "backend/requirements.txt",
            ],
        ),
    )


def test_git_whitespace_check_is_separate_from_working_tree_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[list[str]] = []

    def clean_diff(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(DEV.subprocess, "run", clean_diff)

    assert DEV._check_git_whitespace() is True
    assert calls == [
        ["git", "diff", "--check"],
        ["git", "diff", "--cached", "--check"],
    ]
    output = capsys.readouterr().out
    assert "No whitespace errors" in output
    assert "diffs are clean" not in output


def test_git_whitespace_error_fails_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def whitespace_error(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            2 if "--cached" not in command else 0,
            "README.md:1: trailing whitespace.\n",
            "",
        )

    monkeypatch.setattr(DEV.subprocess, "run", whitespace_error)

    assert DEV._check_git_whitespace() is False


@pytest.mark.parametrize(
    ("porcelain", "expected_clean"),
    [
        ("", True),
        (" M AGENTS.md\n", False),
        ("?? notes.txt\n", False),
        ("!! var/\n", True),
        ("!! frontend/dist/\n", True),
        ("!! .env\n", False),
        ("!! backend/debug.log\n", False),
    ],
)
def test_working_tree_status_classifies_changes_and_ignored_artifacts(
    porcelain: str,
    expected_clean: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def git_status(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert command == [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignored=matching",
        ]
        return subprocess.CompletedProcess(command, 0, porcelain, "")

    monkeypatch.setattr(DEV.subprocess, "run", git_status)

    status_read, working_tree_clean = DEV._inspect_working_tree()

    assert status_read is True
    assert working_tree_clean is expected_clean


def test_clean_verification_is_ready_for_pr_or_tag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = DEV._report_verification_summary(
        [("Git whitespace check", True)],
        working_tree_clean=True,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Verification passed. Working tree clean. Ready for PR/tag." in output


def test_dirty_verification_passes_without_claiming_readiness(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = DEV._report_verification_summary(
        [("Git whitespace check", True)],
        working_tree_clean=False,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Verification passed, but working tree review is required." in output
    assert (
        "Commit/stash/discard uncommitted changes and review local artifacts "
        "before tagging or opening a PR." in output
    )
    assert "Ready for PR/tag" not in output


def test_failed_verification_stays_failed_even_with_dirty_tree(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = DEV._report_verification_summary(
        [("Git whitespace check", False)],
        working_tree_clean=False,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "Verification failed." in output
    assert "Verification passed" not in output
