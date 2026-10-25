"""
Database management layer for Consumer Rights Awareness Portal.
Provides seamless, dual-engine support for:
- Supabase PostgreSQL in production (Render)
- SQLite for local development and test environments
Protects credentials by reading strictly from environment variables and config.
"""

import os
import re
import sqlite3
import urllib.parse
from pathlib import Path
from flask import g, current_app

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def is_postgres_url(url):
    """Determine whether a database connection string targets PostgreSQL."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("postgresql://") or u.startswith("postgres://")


def normalize_db_url(url):
    """
    Ensure the connection URL uses standard postgresql:// prefix and
    enforces SSL for cloud databases (like Supabase) when appropriate.
    """
    if not url:
        return url

    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://"):]

    # For remote Supabase/PostgreSQL connections, enforce SSL mode if unspecified
    if is_postgres_url(normalized):
        parsed = urllib.parse.urlparse(normalized)
        # Check if host is not localhost/127.0.0.1
        if parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1"):
            query_params = urllib.parse.parse_qs(parsed.query)
            if "sslmode" not in query_params:
                delimiter = "&" if parsed.query else "?"
                normalized = f"{normalized}{delimiter}sslmode=require"

    return normalized


def convert_placeholders(sql):
    """
    Convert SQLite-style '?' parameter placeholders to PostgreSQL-style '%s',
    safely ignoring any '?' characters inside single or double quoted literals.
    """
    if not sql or "?" not in sql:
        return sql

    result = []
    in_single_quote = False
    in_double_quote = False
    for char in sql:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append(char)
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(char)
        elif char == '?' and not in_single_quote and not in_double_quote:
            result.append('%s')
        else:
            result.append(char)
    return "".join(result)


class PgCursorWrapper:
    """Wrapper around psycopg2 DictCursor to provide consistent access semantics."""

    def __init__(self, cursor, conn):
        self._cur = cursor
        self._conn = conn

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        if not self._cur.closed:
            self._cur.close()

    def __iter__(self):
        return iter(self._cur)


class PgConnectionWrapper:
    """
    Unified database connection wrapper for PostgreSQL.
    Translates query parameter placeholders ('?' -> '%s') and supports
    direct .execute(), dictionary row indexing, commit, and rollback.
    """

    def __init__(self, raw_conn):
        self._conn = raw_conn
        self.is_postgres = True

    def execute(self, query, args=()):
        converted_sql = convert_placeholders(query)
        cur = self._conn.cursor()
        try:
            if args:
                params = tuple(args) if isinstance(args, (list, tuple)) else args
                cur.execute(converted_sql, params)
            else:
                cur.execute(converted_sql)
            return PgCursorWrapper(cur, self._conn)
        except Exception:
            self._conn.rollback()
            if not cur.closed:
                cur.close()
            raise

    def cursor(self):
        return PgCursorWrapper(self._conn.cursor(), self._conn)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if not self._conn.closed:
            self._conn.close()

    @property
    def closed(self):
        return self._conn.closed


def get_db(db_target=None):
    """
    Get or create a database connection for the current Flask request context.
    Detects whether to use Supabase PostgreSQL (via DATABASE_URL) or SQLite.
    """
    if "db" not in g:
        target = db_target
        if target is None:
            if current_app:
                target = current_app.config.get("DATABASE_URL") or current_app.config.get("DATABASE_PATH")
            else:
                target = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH")

        if target and is_postgres_url(target):
            if not PSYCOPG2_AVAILABLE:
                raise RuntimeError(
                    "psycopg2 is required for PostgreSQL connections. "
                    "Ensure psycopg2-binary is installed from requirements.txt."
                )
            clean_url = normalize_db_url(target)
            raw_conn = psycopg2.connect(
                clean_url,
                cursor_factory=psycopg2.extras.DictCursor,
            )
            g.db = PgConnectionWrapper(raw_conn)
        else:
            # SQLite fallback
            db_path = target or (current_app.config.get("DATABASE_PATH") if current_app else "instance/consumer_rights.db")
            path_obj = Path(db_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            sqlite_conn = sqlite3.connect(str(db_path))
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_conn.execute("PRAGMA foreign_keys = ON;")
            g.db = sqlite_conn

    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db_conn = g.pop("db", None)
    if db_conn is not None:
        try:
            db_conn.close()
        except Exception:
            pass


def query_db(query, args=(), one=False):
    """Execute a parameterized SELECT query across SQLite or PostgreSQL."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), commit=True):
    """Execute a parameterized INSERT/UPDATE/DELETE query across SQLite or PostgreSQL."""
    db_conn = get_db()
    cur = db_conn.execute(query, args)
    if commit:
        db_conn.commit()
    last_id = getattr(cur, "lastrowid", None)
    cur.close()
    return last_id


def test_connection(target=None):
    """
    Actively test connectivity against the targeted database (PostgreSQL or SQLite).
    Returns a tuple of (is_success: bool, status_message: str).
    Guarantees no passwords, credentials, or sensitive URLs are logged or returned.
    """
    if target is None:
        target = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH") or "instance/consumer_rights.db"

    try:
        if is_postgres_url(target):
            if not PSYCOPG2_AVAILABLE:
                return False, "psycopg2 driver not installed"
            clean_url = normalize_db_url(target)
            raw_conn = psycopg2.connect(clean_url, connect_timeout=10)
            with raw_conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            raw_conn.close()
            return True, "Successfully connected to PostgreSQL (Supabase)"
        else:
            path = Path(target)
            if not path.exists():
                return False, f"SQLite database file not found at: {path.name}"
            conn = sqlite3.connect(str(path))
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            conn.close()
            return True, f"Successfully connected to local SQLite ({path.name})"
    except Exception as exc:
        # Sanitize exception message to avoid leaking credentials
        err_msg = str(exc)
        err_msg = re.sub(r":[^:@]+@", ":****@", err_msg)
        return False, f"Connection test failed: {err_msg}"


def init_app(app):
    """Register database teardown with the Flask app."""
    app.teardown_appcontext(close_db)
