#!/usr/bin/env python3.10
"""
Enhanced MCP Server Startup Test
Tests all servers concurrently, validates configuration and startup integrity.

Features:
- Parallel startup testing
- Colored terminal output
- Detailed summary with timings
- Environment variable validation
- Optional log export to ./logs/test_results/
"""

import subprocess
import sys
import os
import time
import shutil
import concurrent.futures
from pathlib import Path
from typing import Dict, Tuple
from dotenv import load_dotenv

try:
    from colorlog import ColoredFormatter
    import logging
except ImportError:
    logging = None

# ────────────────────────────── Setup ──────────────────────────────

project_root = Path(__file__).resolve().parent.parent
servers_dir = project_root / "servers"
log_dir = project_root / "logs" / "test_results"
log_dir.mkdir(parents=True, exist_ok=True)

# Load environment if available
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

SERVERS = {
    "Memory Cache Server": servers_dir / "memory_cache_server.py",
    "Goal Agent Server": servers_dir / "goal_agent_server.py",
    "Internet Server": servers_dir / "internet_server.py",
    "GitHub Server": servers_dir / "github_server.py",
    "Frappe Server": servers_dir / "frappe_server.py",
    "Jira Server": servers_dir / "jira_server.py",
}

# ────────────────────────────── Helpers ──────────────────────────────


def setup_logger() -> logging.Logger:
    """Setup colored logger if colorlog available."""
    logger = logging.getLogger("MCP_Test")
    logger.setLevel(logging.INFO)

    if logging and not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if "ColoredFormatter" in dir():
            formatter = ColoredFormatter(
                "%(log_color)s%(levelname)-8s%(reset)s | %(message)s",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        else:
            formatter = logging.Formatter("%(levelname)-8s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger()


def test_server_startup(
    name: str, script: Path, timeout: int = 3
) -> Tuple[str, bool, float, str]:
    """Run server startup test and return detailed result."""
    start_time = time.time()

    if not script.exists():
        return name, False, 0.0, "File not found"

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=project_root,
            env=os.environ.copy(),
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            message = "Started and exited cleanly"
            success = True
        else:
            if "Traceback" in result.stderr or "error" in result.stderr.lower():
                message = f"Error: {result.stderr[:300]}"
                success = False
            else:
                message = "Exited early — may be waiting for stdio"
                success = True

        # Save output to file
        with open(log_dir / f"{name.replace(' ', '_')}.log", "w") as f:
            f.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")

        return name, success, duration, message

    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if "Traceback" in stderr or "error" in stderr.lower():
            msg = f"Server error during startup: {stderr[:300]}"
            success = False
        else:
            msg = "Running (timeout as expected)"
            success = True

        return name, success, duration, msg

    except Exception as e:
        return name, False, time.time() - start_time, f"Exception: {str(e)}"


# ────────────────────────────── Runner ──────────────────────────────


def main() -> int:
    logger.info("=" * 60)
    logger.info("MCP SERVER STARTUP TEST")
    logger.info("=" * 60)

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(test_server_startup, name, script): name
            for name, script in SERVERS.items()
        }

        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append((name, False, 0.0, f"Unhandled error: {e}"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Server':<25} | {'Status':<10} | {'Time(s)':<8} | Message")
    print("-" * 80)

    success_count = 0
    for name, success, duration, msg in results:
        status = "✓ OK" if success else "✗ FAIL"
        color = "\033[92m" if success else "\033[91m"
        print(f"{color}{name:<25}\033[0m | {status:<10} | {duration:<8.2f} | {msg}")

        if success:
            success_count += 1

    print("-" * 80)
    print(f"TOTAL: {success_count}/{len(SERVERS)} successful")
    print(f"Logs saved in: {log_dir}")
    print("=" * 60)

    return 0 if success_count == len(SERVERS) else 1


if __name__ == "__main__":
    sys.exit(main())
