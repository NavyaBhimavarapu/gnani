"""
VoiceDose - Database Module (SQLite)
====================================
This file manages the SQLite database for VoiceDose.
It defines the schema for patients, medication doses, and voice interaction logs,
and seeds realistic fake data for elderly patients and daily medicine schedules.

Key Responsibilities:
- Manage thread-safe SQLite connection.
- Create and maintain tables: `patients`, `doses`, and `voice_logs`.
- Seed fake patient profile (e.g. Anasuya Devi, 74 yrs) and daily doses.
- Provide CRUD queries for dose status updates and caregiver monitoring.
- Provide a 1-click reset function for clean demo presentations.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.config import DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    """
    Establish and return a connection to the SQLite database.
    Configures row_factory to sqlite3.Row for dictionary-like column access.
    """
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize SQLite database schema.
    Creates tables if they do not exist already.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: Patients (Fake data only)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            conditions TEXT,
            caregiver_name TEXT NOT NULL,
            caregiver_relation TEXT NOT NULL,
            caregiver_phone TEXT NOT NULL,
            preferred_language TEXT NOT NULL DEFAULT 'te-IN',
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table 2: Daily Medication Doses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            slot_name TEXT NOT NULL,         -- 'Morning', 'Afternoon', 'Evening', 'Night'
            scheduled_time TEXT NOT NULL,     -- e.g. '08:00 AM'
            medicine_name TEXT NOT NULL,      -- e.g. 'Amlodipine'
            dosage TEXT NOT NULL,             -- e.g. '5mg'
            purpose TEXT,                     -- e.g. 'Blood Pressure'
            instructions TEXT,                -- e.g. 'Take after breakfast with warm water'
            color_badge TEXT DEFAULT 'emerald',
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'taken', 'missed', 'snoozed'
            logged_at TEXT,                   -- Timestamp when voice response confirmed
            voice_transcript TEXT,            -- Spoken reply captured by Gnani STT
            matched_intent TEXT,              -- 'taken', 'not_yet', 'snooze'
            snooze_until TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Table 3: Voice Interaction Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dose_id INTEGER,
            timestamp TEXT NOT NULL,
            language_code TEXT NOT NULL,
            transcript TEXT,
            matched_intent TEXT,
            confirmation_spoken TEXT,
            success INTEGER DEFAULT 1,
            FOREIGN KEY (dose_id) REFERENCES doses(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_fake_data(force: bool = False) -> None:
    """
    Seed initial fake patient and today's medication schedule.
    If data already exists and force is False, no action is taken.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM patients")
    row = cursor.fetchone()
    if row and row["count"] > 0 and not force:
        conn.close()
        return

    # Clear existing data if forcing reset
    if force:
        cursor.execute("DELETE FROM voice_logs")
        cursor.execute("DELETE FROM doses")
        cursor.execute("DELETE FROM patients")

    # Seed 1: Realistic Fake Patient for Elderly Care
    cursor.execute("""
        INSERT INTO patients (
            id, name, age, gender, conditions,
            caregiver_name, caregiver_relation, caregiver_phone,
            preferred_language, avatar_url
        ) VALUES (
            1,
            'Anasuya Devi',
            74,
            'Female',
            'Hypertension (BP) & Type 2 Diabetes',
            'Karthik Rao',
            'Son',
            '+91 98765 43210',
            'te-IN',
            'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=256&q=80'
        )
    """)

    # Seed 2: Today's 4 scheduled doses
    # Notice: Morning dose is set to 'pending' so it's immediately ready for voice interaction!
    today_date = datetime.now().strftime("%Y-%m-%d")

    doses_data = [
        (
            1, 1, "Morning", "08:00 AM", "Amlodipine", "5 mg",
            "Blood Pressure", "Take after breakfast with a glass of warm water",
            "emerald", "pending", None, None, None, None
        ),
        (
            2, 1, "Afternoon", "01:30 PM", "Metformin", "500 mg",
            "Blood Sugar (Diabetes)", "Take midway through lunch",
            "blue", "pending", None, None, None, None
        ),
        (
            3, 1, "Evening", "08:30 PM", "Atorvastatin", "10 mg",
            "Cholesterol", "Take 30 minutes after dinner",
            "amber", "pending", None, None, None, None
        ),
        (
            4, 1, "Night", "10:00 PM", "Calcium + Vitamin D3", "500 mg",
            "Bone & Joint Health", "Take before bedtime with warm milk",
            "purple", "pending", None, None, None, None
        ),
    ]

    cursor.executemany("""
        INSERT INTO doses (
            id, patient_id, slot_name, scheduled_time, medicine_name, dosage,
            purpose, instructions, color_badge, status, logged_at,
            voice_transcript, matched_intent, snooze_until
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, doses_data)

    # Add a mock initial voice log
    cursor.execute("""
        INSERT INTO voice_logs (
            dose_id, timestamp, language_code, transcript,
            matched_intent, confirmation_spoken, success
        ) VALUES (
            1, ?, 'te-IN', 'సిస్టమ్ ప్రారంభించబడింది (System Initialized)',
            'system', 'VoiceDose is ready to remind.', 1
        )
    """, (datetime.now().strftime("%I:%M %p"),))

    conn.commit()
    conn.close()


def get_patient(patient_id: int = 1) -> Optional[Dict[str, Any]]:
    """Fetch patient profile by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_today_doses(patient_id: int = 1) -> List[Dict[str, Any]]:
    """Fetch all doses scheduled for today for the specified patient."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM doses WHERE patient_id = ? ORDER BY id ASC",
        (patient_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dose_by_id(dose_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single dose record by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doses WHERE id = ?", (dose_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_dose(patient_id: int = 1) -> Optional[Dict[str, Any]]:
    """
    Get the currently active dose that requires elder attention.
    Prioritizes 'pending' or 'snoozed' doses first, then fallback to first dose.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM doses WHERE patient_id = ? AND status IN ('pending', 'snoozed') ORDER BY id ASC LIMIT 1",
        (patient_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM doses WHERE patient_id = ? ORDER BY id ASC LIMIT 1", (patient_id,))
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_dose_status(
    dose_id: int,
    status: str,
    transcript: Optional[str] = None,
    matched_intent: Optional[str] = None,
    snooze_minutes: int = 15
) -> Dict[str, Any]:
    """
    Update dose status ('taken', 'missed', 'snoozed', 'pending')
    and record the voice transcript and timestamp.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%I:%M %p, %b %d")

    snooze_until = None
    if status == "snoozed":
        snooze_time = datetime.now() + timedelta(minutes=snooze_minutes)
        snooze_until = snooze_time.strftime("%I:%M %p")

    cursor.execute("""
        UPDATE doses
        SET status = ?,
            logged_at = ?,
            voice_transcript = COALESCE(?, voice_transcript),
            matched_intent = COALESCE(?, matched_intent),
            snooze_until = ?
        WHERE id = ?
    """, (status, now_str, transcript, matched_intent, snooze_until, dose_id))

    conn.commit()

    cursor.execute("SELECT * FROM doses WHERE id = ?", (dose_id,))
    updated_row = cursor.fetchone()
    conn.close()
    return dict(updated_row) if updated_row else {}


def log_voice_interaction(
    dose_id: int,
    language_code: str,
    transcript: str,
    matched_intent: str,
    confirmation_spoken: str,
    success: bool = True
) -> None:
    """Record an audit trail of each voice interaction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%I:%M:%S %p")
    cursor.execute("""
        INSERT INTO voice_logs (
            dose_id, timestamp, language_code, transcript,
            matched_intent, confirmation_spoken, success
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        dose_id, now_str, language_code, transcript,
        matched_intent, confirmation_spoken, 1 if success else 0
    ))
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 15) -> List[Dict[str, Any]]:
    """Fetch recent voice interaction logs with dose details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, d.medicine_name, d.slot_name
        FROM voice_logs v
        LEFT JOIN doses d ON v.dose_id = d.id
        ORDER BY v.id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_caregiver_stats(patient_id: int = 1) -> Dict[str, Any]:
    """Compute summary statistics for the caregiver dashboard."""
    doses = get_today_doses(patient_id)
    total = len(doses)
    taken = sum(1 for d in doses if d["status"] == "taken")
    missed = sum(1 for d in doses if d["status"] == "missed")
    snoozed = sum(1 for d in doses if d["status"] == "snoozed")
    pending = sum(1 for d in doses if d["status"] == "pending")

    adherence_pct = int((taken / total) * 100) if total > 0 else 0

    return {
        "total": total,
        "taken": taken,
        "missed": missed,
        "snoozed": snoozed,
        "pending": pending,
        "adherence_pct": adherence_pct,
    }


def reset_demo_data() -> Dict[str, Any]:
    """Reset the database to clean demo state."""
    seed_fake_data(force=True)
    return {
        "status": "success",
        "message": "Demo data reset successfully."
    }
