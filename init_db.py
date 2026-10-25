"""
Database initialization and idempotent seed import script.
Supports both Supabase PostgreSQL (production) and SQLite (development/testing).
Idempotent and non-destructive: does NOT delete or overwrite user feedback or existing records.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from db import is_postgres_url, normalize_db_url, convert_placeholders, PgConnectionWrapper


# PostgreSQL Schema
PG_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    name TEXT NOT NULL,
    organisation TEXT NOT NULL,
    authority TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    topic TEXT NOT NULL,
    source_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    last_verified_at TEXT,
    last_verified TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    verified_claims_or_topics TEXT NOT NULL,
    legal_reference TEXT,
    publication_date TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rights (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    full_description TEXT NOT NULL,
    statutory_provision TEXT NOT NULL,
    plain_language_explanation TEXT,
    practical_application TEXT NOT NULL,
    illustrative_scenario TEXT,
    why_it_matters TEXT,
    related_consumer_issues TEXT,
    consumer_responsibilities TEXT,
    key_protections TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    additional_sources TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_verified_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issue_guides (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    typical_situation TEXT,
    problem_statement TEXT NOT NULL,
    step_by_step_procedure TEXT NOT NULL,
    required_evidence TEXT NOT NULL,
    evidence_checklist TEXT,
    relevant_legal_rights TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    additional_sources TEXT,
    official_remedy_channel TEXT,
    caveats_and_escalation TEXT,
    is_published INTEGER DEFAULT 1,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_reviewed_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faqs (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_verified_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    scenario TEXT,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    explanation TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    feedback_type TEXT NOT NULL,
    message TEXT NOT NULL,
    page_url TEXT,
    rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_checks (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    status_code INTEGER,
    status_message TEXT,
    response_time_ms INTEGER,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_audit_logs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    previous_status TEXT,
    new_status TEXT,
    notes TEXT,
    action_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQLite Schema
SQLITE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    name TEXT NOT NULL,
    organisation TEXT NOT NULL,
    authority TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    topic TEXT NOT NULL,
    source_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    last_verified_at TEXT,
    last_verified TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    verified_claims_or_topics TEXT NOT NULL,
    legal_reference TEXT,
    publication_date TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    summary TEXT NOT NULL,
    full_description TEXT NOT NULL,
    statutory_provision TEXT NOT NULL,
    plain_language_explanation TEXT,
    practical_application TEXT NOT NULL,
    illustrative_scenario TEXT,
    why_it_matters TEXT,
    related_consumer_issues TEXT,
    consumer_responsibilities TEXT,
    key_protections TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    additional_sources TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_verified_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issue_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    typical_situation TEXT,
    problem_statement TEXT NOT NULL,
    step_by_step_procedure TEXT NOT NULL,
    required_evidence TEXT NOT NULL,
    evidence_checklist TEXT,
    relevant_legal_rights TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    additional_sources TEXT,
    official_remedy_channel TEXT,
    caveats_and_escalation TEXT,
    is_published INTEGER DEFAULT 1,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_reviewed_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    last_verified_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario TEXT,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL,
    explanation TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_type TEXT NOT NULL,
    message TEXT NOT NULL,
    page_url TEXT,
    rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    status_code INTEGER,
    status_message TEXT,
    response_time_ms INTEGER,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    previous_status TEXT,
    new_status TEXT,
    notes TEXT,
    action_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_rights_slug ON rights(slug);
CREATE INDEX IF NOT EXISTS idx_issue_guides_slug ON issue_guides(slug);
CREATE INDEX IF NOT EXISTS idx_issue_guides_category ON issue_guides(category);
CREATE INDEX IF NOT EXISTS idx_faqs_category ON faqs(category);
CREATE INDEX IF NOT EXISTS idx_sources_code ON sources(code);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(verification_status);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_source_checks_source_id ON source_checks(source_id);
CREATE INDEX IF NOT EXISTS idx_source_audit_logs_source_id ON source_audit_logs(source_id);
"""


def add_missing_columns_sqlite(cursor, table_name, expected_columns):
    """Ensure newly added columns exist in existing SQLite tables."""
    cursor.execute(f"PRAGMA table_info({table_name});")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    for col_name, col_def in expected_columns.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def};")


def migrate_local_data_to_pg(pg_conn, local_sqlite_path):
    """
    Safely migrate existing locally authored data (feedback, link checks, audit logs)
    from local SQLite to Supabase PostgreSQL without duplicates or overwrites.
    """
    if not local_sqlite_path.exists():
        return

    try:
        sq_conn = sqlite3.connect(str(local_sqlite_path))
        sq_conn.row_factory = sqlite3.Row
        sq_cur = sq_conn.cursor()

        # 1. Migrate Feedback
        sq_cur.execute("SELECT feedback_type, message, page_url, rating, created_at FROM feedback")
        feedback_rows = sq_cur.fetchall()
        if feedback_rows:
            cur = pg_conn.execute("SELECT COUNT(*) as c FROM feedback")
            pg_feedback_count = cur.fetchone()["c"]
            if pg_feedback_count == 0:
                print(f"[*] Migrating {len(feedback_rows)} local feedback submissions to PostgreSQL...")
                for row in feedback_rows:
                    pg_conn.execute(
                        """
                        INSERT INTO feedback (feedback_type, message, page_url, rating, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (row["feedback_type"], row["message"], row["page_url"], row["rating"], row["created_at"])
                    )
                pg_conn.commit()

        # 2. Migrate Source Checks if empty
        sq_cur.execute("SELECT source_id, status_code, status_message, response_time_ms, checked_at FROM source_checks")
        check_rows = sq_cur.fetchall()
        if check_rows:
            cur = pg_conn.execute("SELECT COUNT(*) as c FROM source_checks")
            if cur.fetchone()["c"] == 0:
                for row in check_rows:
                    try:
                        pg_conn.execute(
                            """
                            INSERT INTO source_checks (source_id, status_code, status_message, response_time_ms, checked_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (row["source_id"], row["status_code"], row["status_message"], row["response_time_ms"], row["checked_at"])
                        )
                    except Exception:
                        pass
                pg_conn.commit()

        sq_conn.close()
    except Exception as exc:
        print(f"[!] Note on local data migration: {exc}")


def init_database(db_target=None, data_dir=None, db_path=None):
    """
    Idempotently initialize schema and seed foundational content for:
    - Supabase PostgreSQL (when DATABASE_URL is set or passed)
    - SQLite (for local development or testing)
    Does NOT delete or overwrite user feedback or existing records.
    """
    if db_path is not None and db_target is None:
        db_target = db_path

    if db_target is None:
        db_target = os.environ.get("DATABASE_URL")
        if not db_target:
            db_target = os.environ.get("DATABASE_PATH") or str(BASE_DIR / "instance" / "consumer_rights.db")

    if data_dir is None:
        data_dir = BASE_DIR / "data"
    else:
        data_dir = Path(data_dir)

    is_pg = is_postgres_url(db_target)

    if is_pg:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2-binary is required for PostgreSQL initialization.")
        clean_url = normalize_db_url(db_target)
        raw_conn = psycopg2.connect(clean_url, cursor_factory=psycopg2.extras.DictCursor)
        conn = PgConnectionWrapper(raw_conn)
        print("[*] Connected to Supabase PostgreSQL for schema initialization.")
    else:
        db_path = Path(db_target)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        raw_conn = sqlite3.connect(str(db_path))
        raw_conn.row_factory = sqlite3.Row
        raw_conn.execute("PRAGMA foreign_keys = ON;")
        conn = raw_conn
        print(f"[*] Connected to SQLite at: {db_path.name}")

    try:
        # Create Tables
        if is_pg:
            # Execute DDL statements
            for stmt in PG_TABLES_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)
            for stmt in INDEXES_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)
            conn.commit()
        else:
            cursor = conn.cursor()
            cursor.executescript(SQLITE_TABLES_SQL)

            # Migrations helper for any existing SQLite database files
            add_missing_columns_sqlite(cursor, "sources", {
                "title": "TEXT DEFAULT ''",
                "organisation": "TEXT DEFAULT ''",
                "domain": "TEXT DEFAULT ''",
                "topic": "TEXT DEFAULT ''",
                "source_type": "TEXT DEFAULT 'Statute'",
                "summary": "TEXT DEFAULT ''",
                "last_verified_at": "TEXT DEFAULT ''",
                "verification_status": "TEXT DEFAULT 'verified'",
                "verified_claims_or_topics": "TEXT DEFAULT '[]'"
            })
            add_missing_columns_sqlite(cursor, "rights", {
                "plain_language_explanation": "TEXT DEFAULT ''",
                "illustrative_scenario": "TEXT DEFAULT ''",
                "why_it_matters": "TEXT DEFAULT ''",
                "related_consumer_issues": "TEXT DEFAULT '[]'",
                "consumer_responsibilities": "TEXT DEFAULT '[]'",
                "additional_sources": "TEXT DEFAULT '[]'",
                "verification_status": "TEXT DEFAULT 'verified'",
                "last_verified_at": "TEXT DEFAULT ''"
            })
            add_missing_columns_sqlite(cursor, "issue_guides", {
                "typical_situation": "TEXT DEFAULT ''",
                "evidence_checklist": "TEXT DEFAULT '{}'",
                "additional_sources": "TEXT DEFAULT '[]'",
                "caveats_and_escalation": "TEXT DEFAULT ''",
                "verification_status": "TEXT DEFAULT 'verified'",
                "last_reviewed_at": "TEXT DEFAULT ''"
            })
            add_missing_columns_sqlite(cursor, "faqs", {
                "verification_status": "TEXT DEFAULT 'verified'",
                "last_verified_at": "TEXT DEFAULT ''"
            })
            cursor.executescript(INDEXES_SQL)
            conn.commit()

        # 1. Seed Sources
        sources_file = data_dir / "sources.json"
        source_id_map = {}
        if sources_file.exists():
            with open(sources_file, "r", encoding="utf-8") as f:
                sources_data = json.load(f)

            for item in sources_data:
                claims_json = json.dumps(item.get("verified_claims_or_topics", []), ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO sources (
                        code, title, name, organisation, authority, url, domain, topic,
                        source_type, summary, last_verified_at, last_verified,
                        verification_status, verified_claims_or_topics, legal_reference,
                        publication_date, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        title = excluded.title,
                        name = excluded.name,
                        organisation = excluded.organisation,
                        authority = excluded.authority,
                        url = excluded.url,
                        domain = excluded.domain,
                        topic = excluded.topic,
                        source_type = excluded.source_type,
                        summary = excluded.summary,
                        last_verified_at = excluded.last_verified_at,
                        last_verified = excluded.last_verified,
                        verification_status = excluded.verification_status,
                        verified_claims_or_topics = excluded.verified_claims_or_topics,
                        legal_reference = excluded.legal_reference,
                        publication_date = excluded.publication_date,
                        notes = excluded.notes,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        item["code"],
                        item.get("title", item.get("name")),
                        item.get("name", item.get("title")),
                        item.get("organisation", item.get("authority")),
                        item.get("authority", item.get("organisation")),
                        item["url"],
                        item.get("domain", ""),
                        item.get("topic", "Consumer Protection"),
                        item.get("source_type", "Government Publication"),
                        item.get("summary", ""),
                        item.get("last_verified_at", item.get("last_verified", "")),
                        item.get("last_verified", item.get("last_verified_at", "")),
                        item.get("verification_status", "verified"),
                        claims_json,
                        item.get("legal_reference"),
                        item.get("publication_date"),
                        item.get("notes"),
                    ),
                )
            conn.commit()

        # Build source code -> source id mapping
        rows = conn.execute("SELECT id, code FROM sources").fetchall()
        for row in rows:
            source_id_map[row["code"]] = row["id"]

        default_source_id = source_id_map.get("CPA_2019", 1)

        # 2. Seed Rights
        rights_file = data_dir / "rights.json"
        if rights_file.exists():
            with open(rights_file, "r", encoding="utf-8") as f:
                rights_data = json.load(f)

            for item in rights_data:
                source_id = source_id_map.get(item.get("source_code"), default_source_id)
                key_protections_json = json.dumps(item.get("key_protections", []), ensure_ascii=False)
                related_issues_json = json.dumps(item.get("related_consumer_issues", []), ensure_ascii=False)
                responsibilities_json = json.dumps(item.get("consumer_responsibilities", []), ensure_ascii=False)
                additional_sources_json = json.dumps(item.get("additional_sources", []), ensure_ascii=False)

                conn.execute(
                    """
                    INSERT INTO rights (
                        slug, title, legal_name, summary, full_description, statutory_provision,
                        plain_language_explanation, practical_application, illustrative_scenario,
                        why_it_matters, related_consumer_issues, consumer_responsibilities,
                        key_protections, source_id, additional_sources, verification_status,
                        last_verified_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        title = excluded.title,
                        legal_name = excluded.legal_name,
                        summary = excluded.summary,
                        full_description = excluded.full_description,
                        statutory_provision = excluded.statutory_provision,
                        plain_language_explanation = excluded.plain_language_explanation,
                        practical_application = excluded.practical_application,
                        illustrative_scenario = excluded.illustrative_scenario,
                        why_it_matters = excluded.why_it_matters,
                        related_consumer_issues = excluded.related_consumer_issues,
                        consumer_responsibilities = excluded.consumer_responsibilities,
                        key_protections = excluded.key_protections,
                        source_id = excluded.source_id,
                        additional_sources = excluded.additional_sources,
                        verification_status = excluded.verification_status,
                        last_verified_at = excluded.last_verified_at,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        item["slug"],
                        item["title"],
                        item["legal_name"],
                        item["summary"],
                        item["full_description"],
                        item["statutory_provision"],
                        item.get("plain_language_explanation", item.get("summary")),
                        item["practical_application"],
                        item.get("illustrative_scenario", item.get("practical_application")),
                        item.get("why_it_matters", ""),
                        related_issues_json,
                        responsibilities_json,
                        key_protections_json,
                        source_id,
                        additional_sources_json,
                        item.get("verification_status", "verified"),
                        item.get("last_verified_at", "2026-10-25"),
                    ),
                )
            conn.commit()

        # 3. Seed Issue Guides
        guides_file = data_dir / "issue_guides.json"
        if guides_file.exists():
            with open(guides_file, "r", encoding="utf-8") as f:
                guides_data = json.load(f)

            for item in guides_data:
                source_id = source_id_map.get(item.get("source_code"), default_source_id)
                steps_json = json.dumps(item.get("step_by_step_procedure", []), ensure_ascii=False)
                evidence_json = json.dumps(item.get("required_evidence", []), ensure_ascii=False)
                evidence_checklist_json = json.dumps(item.get("evidence_checklist", {}), ensure_ascii=False)
                rights_json = json.dumps(item.get("relevant_legal_rights", []), ensure_ascii=False)
                additional_sources_json = json.dumps(item.get("additional_sources", []), ensure_ascii=False)

                conn.execute(
                    """
                    INSERT INTO issue_guides (
                        slug, title, category, summary, typical_situation, problem_statement,
                        step_by_step_procedure, required_evidence, evidence_checklist,
                        relevant_legal_rights, source_id, additional_sources, official_remedy_channel,
                        caveats_and_escalation, is_published, verification_status, last_reviewed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        title = excluded.title,
                        category = excluded.category,
                        summary = excluded.summary,
                        typical_situation = excluded.typical_situation,
                        problem_statement = excluded.problem_statement,
                        step_by_step_procedure = excluded.step_by_step_procedure,
                        required_evidence = excluded.required_evidence,
                        evidence_checklist = excluded.evidence_checklist,
                        relevant_legal_rights = excluded.relevant_legal_rights,
                        source_id = excluded.source_id,
                        additional_sources = excluded.additional_sources,
                        official_remedy_channel = excluded.official_remedy_channel,
                        caveats_and_escalation = excluded.caveats_and_escalation,
                        is_published = excluded.is_published,
                        verification_status = excluded.verification_status,
                        last_reviewed_at = excluded.last_reviewed_at,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        item["slug"],
                        item["title"],
                        item["category"],
                        item["summary"],
                        item.get("typical_situation", item.get("problem_statement")),
                        item["problem_statement"],
                        steps_json,
                        evidence_json,
                        evidence_checklist_json,
                        rights_json,
                        source_id,
                        additional_sources_json,
                        item.get("official_remedy_channel"),
                        item.get("caveats_and_escalation", ""),
                        item.get("is_published", 1),
                        item.get("verification_status", "verified"),
                        item.get("last_reviewed_at", "2026-10-25"),
                    ),
                )
            conn.commit()

        # 4. Seed FAQs
        faqs_file = data_dir / "faqs.json"
        if faqs_file.exists():
            with open(faqs_file, "r", encoding="utf-8") as f:
                faqs_data = json.load(f)

            for item in faqs_data:
                source_id = source_id_map.get(item.get("source_code"), default_source_id)
                existing = conn.execute("SELECT id FROM faqs WHERE question = ?", (item["question"],)).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE faqs SET
                            category = ?,
                            answer = ?,
                            sort_order = ?,
                            source_id = ?,
                            verification_status = ?,
                            last_verified_at = ?
                        WHERE id = ?;
                        """,
                        (
                            item["category"],
                            item["answer"],
                            item.get("sort_order", 0),
                            source_id,
                            item.get("verification_status", "verified"),
                            item.get("last_verified_at", "2026-10-25"),
                            existing["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO faqs (category, question, answer, sort_order, source_id, verification_status, last_verified_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            item["category"],
                            item["question"],
                            item["answer"],
                            item.get("sort_order", 0),
                            source_id,
                            item.get("verification_status", "verified"),
                            item.get("last_verified_at", "2026-10-25"),
                        ),
                    )
            conn.commit()

        # 5. Seed Quiz Questions
        quiz_file = data_dir / "quiz_questions.json"
        if quiz_file.exists():
            with open(quiz_file, "r", encoding="utf-8") as f:
                quiz_data = json.load(f)

            for item in quiz_data:
                source_id = source_id_map.get(item.get("source_code"), default_source_id)
                existing = conn.execute("SELECT id FROM quiz_questions WHERE question = ?", (item["question"],)).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE quiz_questions SET
                            scenario = ?,
                            option_a = ?,
                            option_b = ?,
                            option_c = ?,
                            option_d = ?,
                            correct_option = ?,
                            explanation = ?,
                            source_id = ?
                        WHERE id = ?;
                        """,
                        (
                            item.get("scenario"),
                            item["option_a"],
                            item["option_b"],
                            item["option_c"],
                            item["option_d"],
                            item["correct_option"],
                            item["explanation"],
                            source_id,
                            existing["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO quiz_questions (scenario, question, option_a, option_b, option_c, option_d, correct_option, explanation, source_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            item.get("scenario"),
                            item["question"],
                            item["option_a"],
                            item["option_b"],
                            item["option_c"],
                            item["option_d"],
                            item["correct_option"],
                            item["explanation"],
                            source_id,
                        ),
                    )
            conn.commit()

        # 6. If PostgreSQL, check and migrate any local feedback or user data
        if is_pg:
            local_instance_db = BASE_DIR / "instance" / "consumer_rights.db"
            migrate_local_data_to_pg(conn, local_instance_db)

        # Report counts
        counts = {}
        for table in ["sources", "rights", "issue_guides", "faqs", "quiz_questions", "feedback", "source_checks"]:
            cur = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            row = cur.fetchone()
            counts[table] = row["cnt"] if row else 0

        engine_name = "PostgreSQL" if is_pg else "SQLite"
        print(f"[SUCCESS] Database initialized successfully on {engine_name}!")
        print("Record counts:")
        for tbl, cnt in counts.items():
            print(f"  - {tbl}: {cnt}")

        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    init_database(db_arg)
