# backend/database.py
# SQLite auto-logging for all feasibility metrics (Tables III–VI)

import sqlite3
from datetime import datetime

DB_PATH = "../data/pilot.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Attempt-level logging (each microphone submission)
    c.execute("""CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        participant_id TEXT,
        group_type TEXT,
        question_id TEXT,
        attempt_num INTEGER,
        db_pass INTEGER,
        stt_text TEXT,
        cosine_score REAL,
        passed INTEGER,
        bypass_used INTEGER,
        latency_ms INTEGER
    )""")

    # Session-level logging (each daily 10-question session)
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        participant_id TEXT,
        day INTEGER,
        completed INTEGER,
        score INTEGER,
        total INTEGER
    )""")

    # Test scores (pre-test, immediate post-test, delayed post-test)
    c.execute("""CREATE TABLE IF NOT EXISTS test_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id TEXT,
        group_type TEXT,
        test_type TEXT,
        score INTEGER,
        total INTEGER,
        timestamp TEXT
    )""")

    conn.commit()
    conn.close()


def log_attempt(
    participant_id: str,
    question_id: str,
    attempt_num: int,
    db_pass: bool,
    stt_text: str,
    cosine_score: float,
    passed: bool,
    bypass_used: bool,
    latency_ms: int,
):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO attempts VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(),
            participant_id,
            "",
            question_id,
            attempt_num,
            int(db_pass),
            stt_text,
            cosine_score,
            int(passed),
            int(bypass_used),
            latency_ms,
        ),
    )
    conn.commit()
    conn.close()


def log_session(participant_id: str, day: int, scores: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sessions VALUES (NULL,?,?,?,?,?,?)",
        (
            datetime.now().isoformat(),
            participant_id,
            day,
            1,
            scores.get("score", 0),
            scores.get("total", 10),
        ),
    )
    conn.commit()
    conn.close()


def log_test_score(participant_id: str, group_type: str, test_type: str, score: int, total: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO test_scores VALUES (NULL,?,?,?,?,?,?)",
        (
            participant_id,
            group_type,
            test_type,
            score,
            total,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def export_csv():
    """Export all data as dict for admin dashboard / SPSS import."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    attempts = [dict(r) for r in conn.execute("SELECT * FROM attempts").fetchall()]
    sessions = [dict(r) for r in conn.execute("SELECT * FROM sessions").fetchall()]
    tests = [dict(r) for r in conn.execute("SELECT * FROM test_scores").fetchall()]
    conn.close()
    return {"attempts": attempts, "sessions": sessions, "test_scores": tests}


def get_feasibility_metrics():
    """
    Compute feasibility metrics from logged data (for Table III auto-fill).
    Returns a dict matching Go/Modify criteria.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Session completion rate
    c.execute("SELECT COUNT(DISTINCT participant_id) FROM sessions")
    n_participants = c.fetchone()[0] or 1
    c.execute("SELECT COUNT(*) FROM sessions WHERE completed=1")
    n_sessions = c.fetchone()[0]
    expected_sessions = n_participants * 12  # 12 days
    session_completion = n_sessions / max(expected_sessions, 1)

    # Attrition
    c.execute("SELECT participant_id, MAX(day) FROM sessions GROUP BY participant_id")
    days_per_participant = c.fetchall()
    attrition = sum(1 for _, d in days_per_participant if d < 12) / max(n_participants, 1)

    # Mean latency
    c.execute("SELECT AVG(latency_ms) FROM attempts")
    mean_latency = c.fetchone()[0] or 0

    # dB gate pass rate
    c.execute("SELECT COUNT(*), SUM(db_pass) FROM attempts")
    total_attempts, db_passes = c.fetchone()
    db_pass_rate = db_passes / max(total_attempts, 1)

    # Cosine score SD
    c.execute(
        "SELECT AVG(cosine_score), AVG(cosine_score*cosine_score) FROM attempts WHERE cosine_score > 0"
    )
    avg_cos, avg_cos_sq = c.fetchone()
    avg_cos = avg_cos or 0
    avg_cos_sq = avg_cos_sq or 0
    cos_sd = (max(0, avg_cos_sq - avg_cos**2)) ** 0.5

    # Bypass activation rate
    c.execute("SELECT COUNT(*), SUM(bypass_used) FROM attempts")
    total_a, bypasses = c.fetchone()
    bypass_rate = bypasses / max(total_a, 1)

    conn.close()

    return {
        "session_completion_rate": round(session_completion, 3),
        "session_completion_go": session_completion >= 0.80,
        "attrition_rate": round(attrition, 3),
        "attrition_go": attrition <= 0.15,
        "mean_latency_ms": round(mean_latency, 0),
        "latency_go": mean_latency < 200,
        "db_pass_rate": round(db_pass_rate, 3),
        "db_pass_go": db_pass_rate >= 0.85,
        "cosine_sd": round(cos_sd, 4),
        "cosine_go": cos_sd < 0.05,
        "bypass_rate": round(bypass_rate, 3),
        "bypass_go": bypass_rate <= 0.20,
    }


init_db()
print(f"[database] DB ready at {DB_PATH}")
