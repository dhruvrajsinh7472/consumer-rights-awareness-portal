"""
Technology for Consumer Rights Awareness (CEP)
Source Link Health & Reachability Maintenance Script

Features:
- Reads canonical URLs from the `sources` registry in SQLite.
- Tests endpoints using lightweight HTTP HEAD with fallback to GET.
- Implements strict connection timeouts and handles redirects gracefully.
- Saves telemetry (HTTP code, latency, timestamp) into the `source_checks` table.
- Preserves legal content-verification status strictly separate from link availability.
- Never marks legal content as verified simply because a web server responds.
- Supports `--limit N` and `--test` modes to respect government servers.
- Clear console reporting with appropriate process exit codes (0, 1, 2).
"""

import argparse
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def check_single_url(url, timeout=5):
    """
    Check single URL health using HTTP HEAD first, falling back to GET if HEAD is disallowed.
    Returns (status_code, status_message, latency_ms).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ConsumerRightsAwarenessPortal/1.0 (Educational CEP)",
        "Accept": "*/*"
    }

    start_time = time.time()
    status_code = None
    status_message = "OK"

    # Step 1: Attempt HTTP HEAD
    try:
        head_req = urllib.request.Request(url, headers=headers, method="HEAD")
        with urllib.request.urlopen(head_req, timeout=timeout) as resp:
            status_code = resp.getcode()
            latency = int((time.time() - start_time) * 1000)
            return status_code, "OK (HEAD)", latency
    except urllib.error.HTTPError as e:
        # If HEAD is disallowed (405 Method Not Allowed) or blocked, fall through to GET
        if e.code in (405, 501, 403):
            pass
        else:
            latency = int((time.time() - start_time) * 1000)
            return e.code, f"HTTP {e.code}: {e.reason}", latency
    except Exception:
        pass  # Fall through to GET on connection/HEAD anomalies

    # Step 2: Fallback to HTTP GET
    start_time = time.time()
    try:
        get_req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(get_req, timeout=timeout) as resp:
            status_code = resp.getcode()
            latency = int((time.time() - start_time) * 1000)
            return status_code, "OK (GET)", latency
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start_time) * 1000)
        return e.code, f"HTTP {e.code}: {e.reason}", latency
    except urllib.error.URLError as e:
        latency = int((time.time() - start_time) * 1000)
        return 0, f"Connection Failed: {e.reason}", latency
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        return 0, f"Error: {str(e)[:80]}", latency


def run_source_health_check(db_path=None, timeout=5, limit=None, test_mode=False):
    """
    Execute health checks on sources stored in SQLite.
    Exit codes:
      0 = Successful execution, all checked endpoints reachable.
      1 = Database or configuration error.
      2 = Completed execution, but one or more checked endpoints failed or timed out.
    """
    if db_path is None:
        db_path = BASE_DIR / "instance" / "consumer_rights.db"
    else:
        db_path = Path(db_path)

    if not db_path.exists():
        print(f"[FATAL ERROR] Database not found at: {db_path}", file=sys.stderr)
        print("Please run 'python init_db.py' to initialize the database schema.", file=sys.stderr)
        return 1

    if test_mode and limit is None:
        limit = 2  # Default to checking just 2 sources in test mode

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT id, code, name, organisation, url, verification_status FROM sources WHERE url IS NOT NULL AND url != '' ORDER BY id"
        if limit:
            query += f" LIMIT {int(limit)}"

        cursor.execute(query)
        sources = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[FATAL ERROR] SQLite failure: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 70)
    print(" Consumer Rights Awareness Portal — Source Link Health Monitor")
    print(f" Checking {len(sources)} source record(s) | Timeout: {timeout}s | Test Mode: {test_mode}")
    print(" NOTE: HTTP reachability is tracked separately from content legal validity.")
    print("=" * 70 + "\n")

    unreachable_count = 0
    checked_count = 0

    for src in sources:
        sid = src["id"]
        code = src["code"]
        name = src["name"]
        url = src["url"]
        content_v_status = src["verification_status"]

        print(f"Checking [{code}] {name[:36]}...")
        status_code, msg, latency = check_single_url(url, timeout=timeout)
        checked_count += 1

        is_healthy = (status_code is not None and 200 <= status_code < 400)
        if not is_healthy:
            unreachable_count += 1

        # Store in source_checks telemetry table
        cursor.execute(
            """
            INSERT INTO source_checks (source_id, status_code, status_message, response_time_ms)
            VALUES (?, ?, ?, ?)
            """,
            (sid, status_code or 0, msg, latency),
        )
        conn.commit()

        status_tag = f"HTTP {status_code}" if status_code else "FAILED"
        health_icon = "[HEALTHY]" if is_healthy else "[UNREACHABLE]"
        print(f"  {health_icon} Result: {status_tag} ({latency}ms) - {msg}")
        print(f"    URL: {url}")
        print(f"    Content Verification Status: [{content_v_status}] (Unmodified)")
        print()

    conn.close()

    print("-" * 70)
    print(f" Summary: {checked_count} checked, {checked_count - unreachable_count} healthy, {unreachable_count} unreachable.")
    print(" Telemetry logged in `source_checks`. Content verification states remain preserved.")
    print("-" * 70 + "\n")

    if unreachable_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check health of official source URLs.")
    parser.add_argument("--db", default=None, help="Path to consumer_rights.db")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds (default 5)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of sources checked")
    parser.add_argument("--test", action="store_true", help="Run test mode (checks 2 sources)")

    cli_args = parser.parse_args()
    code = run_source_health_check(
        db_path=cli_args.db,
        timeout=cli_args.timeout,
        limit=cli_args.limit,
        test_mode=cli_args.test,
    )
    sys.exit(code)
