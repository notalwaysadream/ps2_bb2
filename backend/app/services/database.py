"""
SQLite Database Service for ASHA Visit Records
Uses aiosqlite for async non-blocking operations.
"""
import json
import aiosqlite
from typing import List, Optional
from app.config import DB_PATH
from app.models.visit_record import VisitRecord

def get_seed_records() -> List[VisitRecord]:
    """
    Returns realistic baseline records demonstrating key aspects of PS1:
    1. Routine ANC home visit (Kannada code-mixed) with immunisation & supplements.
    2. High-risk maternal referral (MoHFW Module 6 danger signs: bleeding & severe headache).
    3. Routine HBNC newborn care (Day 7 checkup, weight tracking, BCG/OPV verified).
    4. Emergency newborn danger sign escalation (MoHFW Module 7: high fever & chest indrawing).
    5. Hindi code-mixed ANC visit (local dialect: IFA goli, wazan, TT-1).
    """
    return [
        VisitRecord(
            id="seed-anc-01",
            created_at="2026-11-13T09:15:00Z",
            beneficiary_id="KA-BLR-4408",
            beneficiary_name="Sunita Devi",
            visit_type="ANC 3rd Checkup",
            weight=54.5,
            vaccinations_due=["TT-2 Injection completed"],
            supplements_given=["IFA Tablets (100 days)"],
            next_visit_date="2026-11-28",
            danger_signs_flagged=[],
            is_urgent_referral=False,
            raw_transcript="Beneficiary Sunita Devi ID KA-BLR-4408, 3rd ANC checkup maadide. Weight 54.5 kilo ide. TT-2 injection aagide, IFA tablets kottiddini. Next visit date 28th November.",
            language="kn-IN",
            is_confirmed=True
        ),
        VisitRecord(
            id="seed-referral-02",
            created_at="2026-11-13T10:30:00Z",
            beneficiary_id="KA-MYS-8821",
            beneficiary_name="Priya Gowda",
            visit_type="ANC 4th Checkup (High Risk)",
            weight=58.0,
            vaccinations_due=[],
            supplements_given=["Calcium tablets"],
            next_visit_date="Immediate Referral to PHC",
            danger_signs_flagged=["Per vaginal bleeding", "Severe headache with blurred vision"],
            is_urgent_referral=True,
            raw_transcript="Beneficiary Priya Gowda ID KA-MYS-8821 checkup maadidaaga thumba thale novu mattu vaginal bleeding aagthide antha helidru. Weight 58 kilo. Thatha-kshana PHC ge refer maadbeku.",
            language="kn-IN",
            is_confirmed=True
        ),
        VisitRecord(
            id="seed-hbnc-03",
            created_at="2026-11-13T11:45:00Z",
            beneficiary_id="KA-BLR-1042",
            beneficiary_name="Baby of Lakshmi",
            visit_type="HBNC Day 7 Visit",
            weight=2.85,
            vaccinations_due=["BCG", "OPV-0", "Hepatitis-B birth dose"],
            supplements_given=["Vitamin K (at birth)"],
            next_visit_date="2026-11-20 (HBNC Day 14)",
            danger_signs_flagged=[],
            is_urgent_referral=False,
            raw_transcript="Lakshmi avara maguvina Day 7 HBNC visit aaythu. Maguvina weight 2.85 kilo ide. Feeding chennagi maadtha ide, naabhi clean aagide. Next checkup Day 14 ge.",
            language="kn-IN",
            is_confirmed=True
        ),
        VisitRecord(
            id="seed-referral-04",
            created_at="2026-11-13T13:20:00Z",
            beneficiary_id="KA-MYS-9014",
            beneficiary_name="Baby of Rekha",
            visit_type="HBNC Day 14 (Emergency Referral)",
            weight=3.1,
            vaccinations_due=["Pentavalent-1 pending"],
            supplements_given=[],
            next_visit_date="Immediate Referral to District Hospital (FRU)",
            danger_signs_flagged=["High fever (>38.5 C) in newborn", "Severe chest indrawing", "Refusal to feed / suck"],
            is_urgent_referral=True,
            raw_transcript="Rekha avara maguvige thumba jwara ide, haalu kudithilla mattu chest indrawing kantha ide. Emergency referral to hospital.",
            language="kn-IN",
            is_confirmed=True
        ),
        VisitRecord(
            id="seed-anc-05",
            created_at="2026-11-13T14:10:00Z",
            beneficiary_id="UP-LKO-3312",
            beneficiary_name="Kavita Devi",
            visit_type="ANC 2nd Checkup",
            weight=49.0,
            vaccinations_due=["TT-1 Injection completed"],
            supplements_given=["IFA goli (60 tablets)"],
            next_visit_date="2026-12-10",
            danger_signs_flagged=[],
            is_urgent_referral=False,
            raw_transcript="Kavita Devi ID UP-LKO-3312 ka 2nd ANC checkup hua. Wazan 49 kilo hai. TT-1 injection diya aur 60 IFA goli di. Next checkup 10th December ko hai.",
            language="hi-IN",
            is_confirmed=True
        )
    ]

async def init_db(seed_samples: bool = True):
    """Initializes the SQLite database schema and seeds realistic baseline records if empty."""
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

        if seed_samples:
            for s in get_seed_records():
                await db.execute("""
                    INSERT OR IGNORE INTO visit_records (
                        id, created_at, beneficiary_id, beneficiary_name, visit_type, weight,
                        vaccinations_due, supplements_given, next_visit_date,
                        danger_signs_flagged, is_urgent_referral, raw_transcript,
                        language, is_confirmed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.id,
                    s.created_at,
                    s.beneficiary_id,
                    s.beneficiary_name,
                    s.visit_type,
                    s.weight,
                    json.dumps(s.vaccinations_due),
                    json.dumps(s.supplements_given),
                    s.next_visit_date,
                    json.dumps(s.danger_signs_flagged),
                    1 if s.is_urgent_referral else 0,
                    s.raw_transcript,
                    s.language,
                    1 if s.is_confirmed else 0
                ))
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
