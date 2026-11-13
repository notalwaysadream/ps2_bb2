"""
SQLite Database Service for ASHA Visit Records
Uses aiosqlite for async non-blocking operations.
"""
import json
import aiosqlite
from typing import List, Optional
from app.config import DB_PATH
from app.models.visit_record import VisitRecord

async def init_db():
    """Initializes the SQLite database schema."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visit_records (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                beneficiary_id TEXT,
                beneficiary_name TEXT,
                visit_type TEXT,
                weight REAL,
                vaccinations_due TEXT,
                supplements_given TEXT,
                next_visit_date TEXT,
                danger_signs_flagged TEXT,
                is_urgent_referral INTEGER NOT NULL DEFAULT 0,
                raw_transcript TEXT,
                language TEXT DEFAULT 'kn-IN',
                is_confirmed INTEGER NOT NULL DEFAULT 0
            )
        """)
        try:
            await db.execute("ALTER TABLE visit_records ADD COLUMN beneficiary_name TEXT")
        except Exception:
            pass
        await db.commit()

async def save_record(record: VisitRecord) -> VisitRecord:
    """Inserts or updates a visit record."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                INSERT OR REPLACE INTO visit_records (
                    id, created_at, beneficiary_id, beneficiary_name, visit_type, weight,
                    vaccinations_due, supplements_given, next_visit_date,
                    danger_signs_flagged, is_urgent_referral, raw_transcript,
                    language, is_confirmed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.created_at,
                record.beneficiary_id,
                record.beneficiary_name,
                record.visit_type,
                record.weight,
                json.dumps(record.vaccinations_due),
                json.dumps(record.supplements_given),
                record.next_visit_date,
                json.dumps(record.danger_signs_flagged),
                1 if record.is_urgent_referral else 0,
                record.raw_transcript,
                record.language,
                1 if record.is_confirmed else 0
            ))
            await db.commit()
        except Exception as e:
            if "beneficiary_name" in str(e):
                await db.execute("ALTER TABLE visit_records ADD COLUMN beneficiary_name TEXT")
                await db.commit()
                await db.execute("""
                    INSERT OR REPLACE INTO visit_records (
                        id, created_at, beneficiary_id, beneficiary_name, visit_type, weight,
                        vaccinations_due, supplements_given, next_visit_date,
                        danger_signs_flagged, is_urgent_referral, raw_transcript,
                        language, is_confirmed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id,
                    record.created_at,
                    record.beneficiary_id,
                    record.beneficiary_name,
                    record.visit_type,
                    record.weight,
                    json.dumps(record.vaccinations_due),
                    json.dumps(record.supplements_given),
                    record.next_visit_date,
                    json.dumps(record.danger_signs_flagged),
                    1 if record.is_urgent_referral else 0,
                    record.raw_transcript,
                    record.language,
                    1 if record.is_confirmed else 0
                ))
                await db.commit()
            else:
                raise
    return record

async def get_records(limit: int = 50) -> List[VisitRecord]:
    """Retrieves saved visit records ordered by most recent."""
    records = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM visit_records ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            async for row in cursor:
                records.append(VisitRecord(
                    id=row["id"],
                    created_at=row["created_at"],
                    beneficiary_id=row["beneficiary_id"],
                    beneficiary_name=row["beneficiary_name"] if "beneficiary_name" in row.keys() else None,
                    visit_type=row["visit_type"],
                    weight=row["weight"],
                    vaccinations_due=json.loads(row["vaccinations_due"] or "[]"),
                    supplements_given=json.loads(row["supplements_given"] or "[]"),
                    next_visit_date=row["next_visit_date"],
                    danger_signs_flagged=json.loads(row["danger_signs_flagged"] or "[]"),
                    is_urgent_referral=bool(row["is_urgent_referral"]),
                    raw_transcript=row["raw_transcript"] or "",
                    language=row["language"] or "kn-IN",
                    is_confirmed=bool(row["is_confirmed"])
                ))
    return records

async def get_record_by_id(record_id: str) -> Optional[VisitRecord]:
    """Retrieves a single record by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM visit_records WHERE id = ?", (record_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return VisitRecord(
                id=row["id"],
                created_at=row["created_at"],
                beneficiary_id=row["beneficiary_id"],
                beneficiary_name=row["beneficiary_name"] if "beneficiary_name" in row.keys() else None,
                visit_type=row["visit_type"],
                weight=row["weight"],
                vaccinations_due=json.loads(row["vaccinations_due"] or "[]"),
                supplements_given=json.loads(row["supplements_given"] or "[]"),
                next_visit_date=row["next_visit_date"],
                danger_signs_flagged=json.loads(row["danger_signs_flagged"] or "[]"),
                is_urgent_referral=bool(row["is_urgent_referral"]),
                raw_transcript=row["raw_transcript"] or "",
                language=row["language"] or "kn-IN",
                is_confirmed=bool(row["is_confirmed"])
            )

async def delete_record(record_id: str) -> bool:
    """Deletes a record by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM visit_records WHERE id = ?", (record_id,))
        await db.commit()
        return cursor.rowcount > 0

async def clear_all_records():
    """Wipes all records (useful for fresh hackathon demos)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM visit_records")
        await db.commit()
