"""A.S.I.A development helper CLI.

Usage:
    python scripts/dev.py doctor    – verify local prerequisites
    python scripts/dev.py backend   – start the FastAPI dev server
    python scripts/dev.py frontend  – start the frontend dev server
    python scripts/dev.py test      – run backend and frontend tests
    python scripts/dev.py verify    – run full pre-commit verification
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_ENTRY = BACKEND_DIR / "app" / "main.py"
FRONTEND_PKG = FRONTEND_DIR / "package.json"
FRONTEND_LOCK = FRONTEND_DIR / "package-lock.json"
FRONTEND_NODE_MODULES = FRONTEND_DIR / "node_modules"
RUNTIME_DIR = ROOT / "var"
TICKET_SEED = ROOT / "data" / "fixtures" / "demo_tickets.seed.json"
RUNTIME_TICKETS = RUNTIME_DIR / "demo_tickets.json"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

SUPPORTED_NODE_RANGE = "^20.19.0 || >=22.12.0"
REQUIRED_FRONTEND_SCRIPTS = ("test", "typecheck", "build")

_OBVIOUS_SECRET_RE = re.compile(
    r"""(?ix)
    \b(
        api[_-]?key
        | client[_-]?secret
        | password
        | access[_-]?token
        | auth[_-]?token
    )\b
    \s*[:=]\s*
    ["'][^"'\r\n]{8,}["']
    """
)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

# ASCII-safe markers
_OK = "[OK]"
_FAIL = "[FAIL]"
_WARN = "[WARN]"


def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m" if _USE_COLOUR else text


def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m" if _USE_COLOUR else text


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m" if _USE_COLOUR else text


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m" if _USE_COLOUR else text


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


def _check_python() -> bool:
    """Check that the running Python is ≥ 3.10."""
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info[2]}"
    if (major, minor) >= (3, 10):
        print(f"  {_green(_OK)} Python {version_str}")
        return True
    print(f"  {_red(_FAIL)} Python {version_str} (need >= 3.10)")
    return False


def _parse_semantic_version(version: str) -> tuple[int, int, int] | None:
    """Parse the numeric prefix from versions such as ``v22.12.0``."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if match is None:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )


def _node_version_supported(version: str) -> bool:
    """Return whether a Node version satisfies Vite 7's engine range."""
    parsed = _parse_semantic_version(version)
    if parsed is None:
        return False
    major, minor, patch = parsed
    if major == 20:
        return (major, minor, patch) >= (20, 19, 0)
    return (major, minor, patch) >= (22, 12, 0)


def _check_node() -> bool:
    """Check that Node exists and satisfies the frontend engine range."""
    node = shutil.which("node")
    if node is None:
        print(f"  {_red(_FAIL)} Node.js - not found on PATH")
        print(f"    Install Node.js {SUPPORTED_NODE_RANGE}.")
        return False

    try:
        result = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"  {_red(_FAIL)} Node.js - version check failed: {exc}")
        return False

    version = result.stdout.strip() or result.stderr.strip()
    if result.returncode == 0 and _node_version_supported(version):
        print(
            f"  {_green(_OK)} Node.js {version.removeprefix('v')} "
            f"(supported: {SUPPORTED_NODE_RANGE})"
        )
        return True

    shown_version = version.removeprefix("v") or "unknown"
    print(
        f"  {_red(_FAIL)} Node.js {shown_version} is unsupported "
        f"(need {SUPPORTED_NODE_RANGE})"
    )
    return False


def _check_command(name: str, version_flag: str = "--version") -> bool:
    """Check that *name* is on PATH and can report its version."""
    path = shutil.which(name)
    if path is None:
        print(f"  {_red(_FAIL)} {name} - not found on PATH")
        return False
    try:
        result = subprocess.run(
            [path, version_flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode != 0:
            detail = output.splitlines()[0] if output else "version check failed"
            print(f"  {_red(_FAIL)} {name} - {detail}")
            return False
        version = output.splitlines()[0] if output else f"found at {path}"
        print(f"  {_green(_OK)} {name} {version}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  {_red(_FAIL)} {name} - error: {exc}")
        return False


def _check_python_module(module: str) -> bool:
    """Check that a Python module can be imported."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"  {_green(_OK)} Python module '{module}'")
            return True
        print(f"  {_red(_FAIL)} Python module '{module}' could not be imported")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  {_red(_FAIL)} Python module '{module}' - error: {exc}")
        return False


def _check_path(label: str, path: Path, *, required: bool = True) -> bool:
    """Check that *path* exists on disk."""
    if path.exists():
        print(f"  {_green(_OK)} {label} exists ({path.relative_to(ROOT)})")
        return True
    marker = _red(_FAIL) if required else _yellow(_WARN)
    print(f"  {marker} {label} missing ({path.relative_to(ROOT)})")
    return not required


def _check_backend_import() -> bool:
    """Import the actual FastAPI application from the backend directory."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import app; assert app is not None",
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode == 0:
        print(f"  {_green(_OK)} Backend application imports successfully")
        return True

    print(f"  {_red(_FAIL)} Backend application import failed")
    detail_lines = (result.stderr.strip() or result.stdout.strip()).splitlines()
    if detail_lines:
        print(f"    {detail_lines[-1]}")
    return False


def _check_frontend_scripts() -> bool:
    """Validate required npm scripts in the frontend manifest."""
    try:
        manifest = json.loads(FRONTEND_PKG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"  {_red(_FAIL)} frontend/package.json is missing")
        return False
    except json.JSONDecodeError as exc:
        print(f"  {_red(_FAIL)} frontend/package.json is invalid JSON: {exc}")
        return False

    scripts = manifest.get("scripts")
    if not isinstance(scripts, dict):
        print(f"  {_red(_FAIL)} frontend/package.json has no scripts object")
        return False

    missing = [
        name
        for name in REQUIRED_FRONTEND_SCRIPTS
        if not isinstance(scripts.get(name), str) or not scripts[name].strip()
    ]
    if missing:
        print(
            f"  {_red(_FAIL)} Missing frontend scripts: "
            f"{', '.join(missing)}"
        )
        return False

    engines = manifest.get("engines")
    node_range = engines.get("node") if isinstance(engines, dict) else None
    if node_range != SUPPORTED_NODE_RANGE:
        print(
            f"  {_red(_FAIL)} frontend/package.json must declare Node "
            f"{SUPPORTED_NODE_RANGE}"
        )
        return False

    print(
        f"  {_green(_OK)} Frontend scripts available: "
        f"{', '.join(REQUIRED_FRONTEND_SCRIPTS)}; "
        f"Node {SUPPORTED_NODE_RANGE}"
    )
    return True


def _check_frontend_dependencies() -> bool:
    """Check that the lockfile dependencies are installed and complete."""
    if not FRONTEND_NODE_MODULES.is_dir():
        print(f"  {_red(_FAIL)} frontend/node_modules is missing")
        print("    Run: cd frontend && npm ci")
        return False

    npm = _npm_command()
    if npm is None:
        print(f"  {_red(_FAIL)} npm - not found on PATH")
        return False

    result = subprocess.run(
        [npm, "ls", "--depth=0"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        print(f"  {_green(_OK)} Frontend dependencies are installed")
        return True

    print(f"  {_red(_FAIL)} Frontend dependencies are incomplete or invalid")
    print("    Run: cd frontend && npm ci")
    return False


def _check_runtime_writable() -> bool:
    """Verify that the ignored local runtime directory can be written."""
    probe_path: Path | None = None
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".doctor-",
            suffix=".tmp",
            dir=RUNTIME_DIR,
            delete=False,
        ) as probe:
            probe.write("ok\n")
            probe_path = Path(probe.name)
    except OSError as exc:
        print(f"  {_red(_FAIL)} Runtime directory is not writable: {exc}")
        return False
    finally:
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)

    print(f"  {_green(_OK)} Runtime directory is writable (var/)")
    return True


def _check_env_configuration() -> bool:
    """Check the optional dotenv contract for the current milestone."""
    if not ENV_EXAMPLE.exists():
        print(f"  {_green(_OK)} No .env configuration required for v0.1")
        return True
    if ENV_FILE.exists():
        print(f"  {_green(_OK)} .env exists for the declared environment")
        return True

    print(f"  {_red(_FAIL)} .env.example exists but .env is missing")
    print("    Copy .env.example to .env and fill the required local values.")
    return False


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Verify that this machine can run the complete local project."""
    print(_bold("Checking full local project readiness...\n"))
    results: list[bool] = []

    print(_bold("[Runtime]"))
    results.append(_check_python())
    results.append(_check_node())
    results.append(_check_command("npm"))

    print(f"\n{_bold('[Backend]')}")
    for module in (
        "fastapi",
        "uvicorn",
        "pydantic",
        "pytest",
        "httpx",
        "anyio",
    ):
        results.append(_check_python_module(module))
    results.append(_check_path("backend entry", BACKEND_ENTRY, required=True))
    results.append(_check_backend_import())

    print(f"\n{_bold('[Frontend]')}")
    results.append(
        _check_path("frontend package.json", FRONTEND_PKG, required=True)
    )
    results.append(
        _check_path("frontend package-lock.json", FRONTEND_LOCK, required=True)
    )
    results.append(_check_frontend_scripts())
    results.append(_check_frontend_dependencies())

    print(f"\n{_bold('[Local state]')}")
    results.append(_check_runtime_writable())
    results.append(_check_env_configuration())

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed.")

    if all(results):
        print(_green("\nEnvironment is ready to run the full project."))
        return 0

    print(
        _yellow(
            "\nEnvironment is not ready yet. "
            "Follow the remediation hints above."
        )
    )
    return 1


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


def cmd_backend(_args: argparse.Namespace) -> int:
    """Start the FastAPI development server."""
    if not BACKEND_ENTRY.exists():
        print(_red(f"Error: {BACKEND_ENTRY.relative_to(ROOT)} not found."))
        print("Create the backend entry point first, then retry.")
        return 1

    print(_bold("Starting FastAPI dev server..."))
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=BACKEND_DIR,
        )
        return proc.returncode
    except KeyboardInterrupt:
        print("\nBackend server stopped.")
        return 0


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------


def _npm_command() -> str | None:
    """Return an executable npm command for the current platform."""
    if sys.platform == "win32":
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which("npm")


def cmd_frontend(_args: argparse.Namespace) -> int:
    """Start the frontend dev server (npm run dev)."""
    if not FRONTEND_PKG.exists():
        print(_red(f"Error: {FRONTEND_PKG.relative_to(ROOT)} not found."))
        print("Initialise the frontend project first, then retry.")
        return 1

    npm = _npm_command()
    if npm is None:
        print(_red("Error: npm not found on PATH."))
        return 1

    print(_bold("Starting frontend dev server..."))
    try:
        proc = subprocess.run(
            [npm, "run", "dev"],
            cwd=FRONTEND_DIR,
        )
        return proc.returncode
    except KeyboardInterrupt:
        print("\nFrontend server stopped.")
        return 0


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def cmd_test(_args: argparse.Namespace) -> int:
    """Run the fast backend and frontend test loop."""
    tests_dir = BACKEND_DIR / "tests"
    has_tests = tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))

    if not has_tests:
        print(
            _red(
                "No backend tests found yet.\n"
                f"Add test files to {tests_dir.relative_to(ROOT)}/ and re-run."
            )
        )
        return 1

    results = [
        _run_verification_command(
            "Backend tests",
            [sys.executable, "-m", "pytest", "-v", str(tests_dir)],
            cwd=BACKEND_DIR,
        )
    ]

    npm = _npm_command()
    if npm is None:
        print(_red(f"\n{_FAIL} npm not found on PATH."))
        results.append(False)
    else:
        results.append(
            _run_verification_command(
                "Frontend tests",
                [npm, "run", "test"],
                cwd=FRONTEND_DIR,
            )
        )

    passed = sum(results)
    print(f"\n{passed}/{len(results)} test suites passed.")
    return 0 if all(results) else 1


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def _run_verification_command(
    label: str,
    command: list[str],
    *,
    cwd: Path,
) -> bool:
    """Run one visible verification command and return whether it passed."""
    print(f"\n{_bold(f'[{label}]')}", flush=True)
    try:
        result = subprocess.run(command, cwd=cwd)
    except FileNotFoundError:
        print(_red(f"{_FAIL} Command not found: {command[0]}"))
        return False
    except KeyboardInterrupt:
        print(_red(f"\n{_FAIL} Verification interrupted."))
        return False

    if result.returncode == 0:
        print(_green(f"{_OK} {label}"))
        return True
    print(_red(f"{_FAIL} {label} (exit code {result.returncode})"))
    return False


def _check_runtime_hygiene() -> bool:
    """Ensure runtime state is ignored and the committed seed stays empty."""
    print(f"\n{_bold('[Runtime hygiene]')}")
    errors: list[str] = []

    tracked = subprocess.run(
        ["git", "ls-files", "--", "var"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if tracked.returncode != 0:
        errors.append("Could not inspect tracked runtime files.")
    elif tracked.stdout.strip():
        errors.append("Files under var/ must not be tracked by Git.")

    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "-q",
            "--",
            str(RUNTIME_TICKETS.relative_to(ROOT)),
        ],
        cwd=ROOT,
    )
    if ignored.returncode != 0:
        errors.append("var/demo_tickets.json is not ignored by Git.")

    try:
        seed = json.loads(TICKET_SEED.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Ticket seed cannot be read as JSON: {exc}")
    else:
        if seed != []:
            errors.append(
                "data/fixtures/demo_tickets.seed.json must remain an empty list."
            )

    if errors:
        for error in errors:
            print(_red(f"  {_FAIL} {error}"))
        return False

    print(_green(f"  {_OK} Runtime state is ignored; ticket seed is clean."))
    return True


def _candidate_files() -> tuple[Path, ...]:
    """Return tracked and untracked non-ignored files for repository checks."""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed")
    relative_paths = result.stdout.decode("utf-8").split("\0")
    return tuple(ROOT / path for path in relative_paths if path)


def _check_obvious_secrets() -> bool:
    """Flag obvious quoted credential assignments without printing values."""
    print(f"\n{_bold('[Obvious secret scan]')}")
    findings: list[str] = []

    try:
        candidate_files = _candidate_files()
    except RuntimeError as exc:
        print(_red(f"  {_FAIL} {exc}"))
        return False

    for path in candidate_files:
        try:
            if path.stat().st_size > 1_000_000:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if _OBVIOUS_SECRET_RE.search(line):
                findings.append(
                    f"{path.relative_to(ROOT).as_posix()}:{line_number}"
                )

    if findings:
        print(
            _red(
                f"  {_FAIL} Possible credential assignments found "
                "(values intentionally hidden):"
            )
        )
        for finding in findings:
            print(f"    - {finding}")
        return False

    print(_green(f"  {_OK} No obvious credential assignments found."))
    return True


def _check_git_whitespace() -> bool:
    """Check staged and unstaged diffs for whitespace errors."""
    print(f"\n{_bold('[Git diff check]')}")
    checks = (
        ("unstaged", ["git", "diff", "--check"]),
        ("staged", ["git", "diff", "--cached", "--check"]),
    )
    passed = True

    for label, command in checks:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            passed = False
            print(_red(f"  {_FAIL} {label} diff has whitespace errors."))
            if result.stdout.strip():
                print(result.stdout.rstrip())
            if result.stderr.strip():
                print(result.stderr.rstrip())

    if passed:
        print(_green(f"  {_OK} Staged and unstaged diffs are clean."))
    return passed


def cmd_verify(_args: argparse.Namespace) -> int:
    """Run the complete pre-commit and pre-PR verification suite."""
    print(_bold("Running full project verification..."))
    results: list[tuple[str, bool]] = []

    results.append(
        (
            "Backend tests",
            _run_verification_command(
                "Backend tests",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    str(BACKEND_DIR / "tests"),
                ],
                cwd=BACKEND_DIR,
            ),
        )
    )

    npm = _npm_command()
    if npm is None:
        print(_red(f"\n{_FAIL} npm not found on PATH."))
        results.extend(
            (
                ("Frontend tests", False),
                ("Frontend typecheck", False),
                ("Frontend build", False),
            )
        )
    else:
        results.append(
            (
                "Frontend tests",
                _run_verification_command(
                    "Frontend tests",
                    [npm, "run", "test"],
                    cwd=FRONTEND_DIR,
                ),
            )
        )
        results.append(
            (
                "Frontend typecheck",
                _run_verification_command(
                    "Frontend typecheck",
                    [npm, "run", "typecheck"],
                    cwd=FRONTEND_DIR,
                ),
            )
        )
        results.append(
            (
                "Frontend build",
                _run_verification_command(
                    "Frontend build",
                    [npm, "run", "build"],
                    cwd=FRONTEND_DIR,
                ),
            )
        )

    results.extend(
        (
            ("Runtime hygiene", _check_runtime_hygiene()),
            ("Obvious secret scan", _check_obvious_secrets()),
            ("Git diff check", _check_git_whitespace()),
        )
    )

    passed = sum(result for _label, result in results)
    total = len(results)
    print(f"\n{_bold('Verification summary')}")
    for label, result in results:
        marker = _green(_OK) if result else _red(_FAIL)
        print(f"  {marker} {label}")
    print(f"\n{passed}/{total} verification steps passed.")

    if passed == total:
        print(_green("\nReady to commit / ready for PR."))
        return 0
    print(_red("\nVerification failed. Fix the checks above and retry."))
    return 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dev",
        description="A.S.I.A development helper",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Check local prerequisites")
    sub.add_parser("backend", help="Run FastAPI dev server")
    sub.add_parser("frontend", help="Run frontend dev server (npm)")
    sub.add_parser("test", help="Run backend and frontend tests")
    sub.add_parser("verify", help="Run full pre-commit verification")

    args = parser.parse_args()

    dispatch = {
        "doctor": cmd_doctor,
        "backend": cmd_backend,
        "frontend": cmd_frontend,
        "test": cmd_test,
        "verify": cmd_verify,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
