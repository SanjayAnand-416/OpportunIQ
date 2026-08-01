import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite


DATABASE_PATH = os.getenv("DATABASE_PATH", "opportuniq.db")


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield a SQLite connection configured for dictionary-like rows."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """Initialize the SQLite database schema."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS student_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT UNIQUE,
                name TEXT,
                email TEXT,
                year_of_study TEXT,
                graduation_year INTEGER,
                degree TEXT,
                college TEXT,
                target_roles TEXT,
                phone TEXT,
                education TEXT,
                skills TEXT,
                location TEXT,
                opportunity_type TEXT,
                experience TEXT,
                projects TEXT,
                raw_resume_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "profile_id": "TEXT",
            "year_of_study": "TEXT",
            "graduation_year": "INTEGER",
            "degree": "TEXT",
            "college": "TEXT",
            "target_roles": "TEXT",
            "location": "TEXT",
            "opportunity_type": "TEXT",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE student_profiles ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT UNIQUE,
                session_id TEXT,
                profile_id TEXT,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                company TEXT,
                platform TEXT,
                organization TEXT,
                location TEXT,
                url TEXT,
                url_hash TEXT,
                description TEXT,
                deadline TEXT,
                stipend_or_prize TEXT,
                eligibility TEXT,
                skills_required TEXT,
                also_on TEXT,
                match_score REAL DEFAULT 0,
                urgency_score REAL DEFAULT 0,
                combined_score REAL DEFAULT 0,
                is_expired INTEGER DEFAULT 0,
                opportunity_type TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, external_id)
            )
            """
        )
        for column_name, column_type in {
            "opportunity_id": "TEXT",
            "session_id": "TEXT",
            "profile_id": "TEXT",
            "company": "TEXT",
            "platform": "TEXT",
            "url_hash": "TEXT",
            "stipend_or_prize": "TEXT",
            "eligibility": "TEXT",
            "skills_required": "TEXT",
            "also_on": "TEXT",
            "match_score": "REAL DEFAULT 0",
            "urgency_score": "REAL DEFAULT 0",
            "combined_score": "REAL DEFAULT 0",
            "is_expired": "INTEGER DEFAULT 0",
            "fetched_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE opportunities ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_session_id
            ON opportunities(session_id)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_profile_id
            ON opportunities(profile_id)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_opportunities_fetched_at
            ON opportunities(fetched_at)
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                deadline_at TEXT,
                context TEXT,
                email_message_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS deadline_registry (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                opportunity_id TEXT,
                title TEXT NOT NULL,
                organization TEXT,
                deadline_datetime TIMESTAMP,
                event_type TEXT,
                action_required TEXT,
                notes TEXT,
                source TEXT NOT NULL,
                gmail_message_id TEXT,
                confidence REAL,
                needs_review BOOLEAN DEFAULT FALSE,
                is_completed BOOLEAN DEFAULT FALSE,
                is_cancelled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "profile_id": "TEXT",
            "opportunity_id": "TEXT",
            "title": "TEXT",
            "organization": "TEXT",
            "deadline_datetime": "TIMESTAMP",
            "event_type": "TEXT",
            "action_required": "TEXT",
            "notes": "TEXT",
            "source": "TEXT",
            "gmail_message_id": "TEXT",
            "confidence": "REAL",
            "needs_review": "BOOLEAN DEFAULT FALSE",
            "is_completed": "BOOLEAN DEFAULT FALSE",
            "is_cancelled": "BOOLEAN DEFAULT FALSE",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE deadline_registry ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_deadline_registry_profile_id
            ON deadline_registry(profile_id)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_deadline_registry_deadline_datetime
            ON deadline_registry(deadline_datetime)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_deadline_registry_profile_deadline
            ON deadline_registry(profile_id, deadline_datetime)
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_deadline_registry_needs_review
            ON deadline_registry(needs_review)
            """
        )
        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_deadline_registry_gmail_unique
            ON deadline_registry(profile_id, gmail_message_id)
            WHERE gmail_message_id IS NOT NULL
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS gmail_connections (
                profile_id TEXT PRIMARY KEY,
                email TEXT,
                connected BOOLEAN DEFAULT FALSE,
                last_scanned TIMESTAMP,
                deadlines_found INTEGER DEFAULT 0,
                needs_review INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deadline_id INTEGER,
                channel TEXT NOT NULL,
                message TEXT NOT NULL,
                scheduled_for TEXT,
                sent_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(deadline_id) REFERENCES deadlines(id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                deadline_id TEXT,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                channel TEXT NOT NULL,
                reminder_offset TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                delivery_status TEXT DEFAULT 'created',
                error_message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "profile_id": "TEXT",
            "deadline_id": "TEXT",
            "subject": "TEXT",
            "message": "TEXT",
            "channel": "TEXT",
            "reminder_offset": "TEXT",
            "is_read": "BOOLEAN DEFAULT FALSE",
            "delivery_status": "TEXT DEFAULT 'created'",
            "error_message": "TEXT",
            "sent_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE notifications ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_profile_id "
            "ON notifications(profile_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_deadline_id "
            "ON notifications(deadline_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read "
            "ON notifications(is_read)"
        )
        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_deadline_offset_channel
            ON notifications(deadline_id, reminder_offset, channel)
            WHERE deadline_id IS NOT NULL AND reminder_offset IS NOT NULL
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id TEXT UNIQUE,
                thread_id TEXT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                snippet TEXT,
                body TEXT,
                received_at TEXT,
                is_processed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_opportunities (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                status TEXT DEFAULT 'Not Applied',
                notes TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "profile_id": "TEXT",
            "opportunity_id": "TEXT",
            "status": "TEXT DEFAULT 'Not Applied'",
            "notes": "TEXT",
            "saved_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE saved_opportunities ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute("CREATE INDEX IF NOT EXISTS idx_saved_profile_id ON saved_opportunities(profile_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_saved_opportunity_id ON saved_opportunities(opportunity_id)")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_profile_opportunity ON saved_opportunities(profile_id, opportunity_id)")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS gap_analyses (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                opportunity_id TEXT,
                target_role TEXT NOT NULL,
                analysis_mode TEXT NOT NULL,
                overall_assessment TEXT NOT NULL,
                missing_skills TEXT NOT NULL,
                suggested_projects TEXT NOT NULL,
                evidence_data TEXT NOT NULL,
                jd_snippet TEXT,
                profile_snapshot TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column_name, column_type in {
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }.items():
            try:
                await db.execute(
                    f"ALTER TABLE gap_analyses ADD COLUMN {column_name} {column_type}"
                )
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_gap_analyses_profile "
            "ON gap_analyses(profile_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_gap_analyses_opportunity "
            "ON gap_analyses(opportunity_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_gap_analyses_generated_at "
            "ON gap_analyses(generated_at)"
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_gap_role_profile "
            "ON gap_analyses(profile_id) "
            "WHERE opportunity_id IS NULL AND analysis_mode = 'profile_vs_role'"
        )
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_gap_profile_opportunity "
            "ON gap_analyses(profile_id, opportunity_id) "
            "WHERE opportunity_id IS NOT NULL "
            "AND analysis_mode = 'profile_vs_opportunity'"
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_settings (
                profile_id TEXT PRIMARY KEY,
                r_7d BOOLEAN DEFAULT TRUE,
                r_3d BOOLEAN DEFAULT TRUE,
                r_1d BOOLEAN DEFAULT TRUE,
                r_same_day BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()
