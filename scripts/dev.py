"""A.S.I.A development helper CLI.

Usage:
    python scripts/dev.py doctor    – verify local prerequisites
    python scripts/dev.py backend   – start the FastAPI dev server
    python scripts/dev.py frontend  – start the frontend dev server
    python scripts/dev.py test      – run backend tests
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_ENTRY = BACKEND_DIR / "app" / "main.py"
FRONTEND_PKG = FRONTEND_DIR / "package.json"

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
        version = output.splitlines()[0] if output else f"{name} found at {path}"
        print(f"  {_green(_OK)} {version}")
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


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Run environment checks and report results."""
    print(_bold("Running doctor checks...\n"))
    results: list[bool] = []

    print(_bold("[Runtime]"))
    results.append(_check_python())

    print(f"\n{_bold('[Tools]')}")
    results.append(_check_command("node"))
    results.append(_check_command("npm"))

    print(f"\n{_bold('[Python packages]')}")
    for module in (
        "fastapi",
        "uvicorn",
        "pydantic",
        "pytest",
        "httpx",
        "anyio",
    ):
        results.append(_check_python_module(module))

    print(f"\n{_bold('[Project files]')}")
    results.append(_check_path("backend entry", BACKEND_ENTRY, required=True))
    results.append(
        _check_path("frontend package.json", FRONTEND_PKG, required=True)
    )

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed.")

    if all(results):
        print(_green("\nAll good - ready to develop!"))
        return 0

    print(_yellow("\nSome checks did not pass. See above for details."))
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
    """Run backend tests with pytest, if available."""
    tests_dir = BACKEND_DIR / "tests"
    has_tests = tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))

    if not has_tests:
        print(
            _yellow(
                "No backend tests found yet.\n"
                f"Add test files to {tests_dir.relative_to(ROOT)}/ and re-run."
            )
        )
        return 0

    print(_bold("Running backend tests..."), flush=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", str(tests_dir)],
            cwd=BACKEND_DIR,
        )
        return proc.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted.")
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
    sub.add_parser("test", help="Run backend tests")

    args = parser.parse_args()

    dispatch = {
        "doctor": cmd_doctor,
        "backend": cmd_backend,
        "frontend": cmd_frontend,
        "test": cmd_test,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
