# Software Specification Document — TOEIC Active Recall Pilot System

**Document Version:** 1.0
**Date:** 2026-05-27
**Author:** Peter (Chihlee University of Technology)
**Deployment:** VPS 5.78.177.52, Cloudflare Tunnel

---

## 1. System Overview

### 1.1 Purpose
A web-based game-based learning (GBL) platform for a pilot study investigating the Active Recall Effect in mobile TOEIC preparation. The system implements a 3-layer verification pipeline (dB gate → STT → semantic similarity) and serves as the data-collection instrument for the ICSI 2026 paper: *"AI-Supervised Vocalization via Whisper STT and Game-Based Learning Mechanics for Corrective Feedback in Mobile TOEIC Preparation: A Pilot Feasibility Study."*

### 1.2 Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (Vanilla HTML/JS/CSS)       │
│  index.html → game.html / test.html → complete.html   │
│  Admin: admin.html                                     │
├──────────────────────────────────────────────────────┤
│          FastAPI Backend (Python 3.11)                 │
│  /api/verify     ← 3-layer pipeline                   │
│  /api/verify-text ← Bypass mode                       │
│  /api/questions  ← TOEIC question bank                │
│  /api/session/complete ← Session logging              │
│  /api/test/submit ← Test score logging                │
│  /api/admin/*    ← Metrics/export                     │
├────────────┬─────────────────────────────────────────┤
│  Pipeline  │  Layer 1: dB Gate (numpy RMS)            │
│            │  Layer 2: Groq Whisper (whisper-v3-turbo)│
│            │  Layer 3: Cosine Similarity (sentence-   │
│            │           transformers MiniLM-L12-v2)    │
├────────────┴─────────────────────────────────────────┤
│              SQLite Database (pilot.db)                │
│  tables: attempts, sessions, test_scores              │
└──────────────────────────────────────────────────────┘
```

### 1.3 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI (Python) | 0.136 |
| ASGI Server | Uvicorn | 0.48 |
| STT | Groq Whisper API | large-v3-turbo |
| NLP Embeddings | sentence-transformers | 5.5 (MiniLM-L12-v2) |
| Database | SQLite3 | Built-in |
| Frontend | Vanilla HTML/CSS/JS | ES6 |
| Audio Recording | MediaRecorder API | WebM |
| Deployment | Cloudflare Tunnel | 2026.5.2 |

---

## 2. Functional Specification

### 2.1 User Flows

#### 2.1.1 Landing & Session Start (index.html)
- User enters Participant ID (e.g., P001)
- Selects Group: A (Control — passive reading) or B (Experimental — Active Recall)
- Selects Day (1–12) and Mode (Practice / Pre-test / Post-test)
- On submit → redirects to game.html or test.html with URL params

#### 2.1.2 Practice Session (game.html)

**Group B — Experimental (Active Recall):**
```
For each of 10 questions:
  1. Read question stem + 4 options (A/B/C/D)
  2. Click answer
     ├─ CORRECT → +1 score, +1 streak, reward animation, Next button
     └─ WRONG   → Show explanation + Active Recall Zone
                   ├─ Attempt 1: Press-hold Record → Groq Whisper STT
                   │  ├─ PASS (cosine ≥ 0.80) → +10 points, Next
                   │  └─ FAIL → Attempt 2
                   ├─ Attempt 2: Record again
                   │  ├─ PASS → +10 points, Next
                   │  └─ FAIL → Bypass button appears
                   └─ Bypass: Type explanation → cosine check
                      ├─ PASS → +5 points, Next
                      └─ FAIL → Still allowed to proceed
```

**Group A — Control (Passive Reading):**
```
For each of 10 questions:
  1. Read question stem + 4 options
  2. Click answer
     ├─ CORRECT → +1 score, +1 streak, Next
     └─ WRONG   → Show explanation (passive), Next
```

#### 2.1.3 Pre/Post Test (test.html)
- 30 questions, no GBL mechanics
- No Active Recall zone for either group
- Keyboard navigation (← → arrows)
- Submit button at the end
- Score auto-submitted to server

#### 2.1.4 Session Complete (complete.html)
- Displays: Score, Max Streak, First-Try Correct Count
- Motivational message based on performance
- Link to start next session

#### 2.1.5 Admin Dashboard (admin.html)
- Real-time feasibility metrics (6 Go/Modify criteria)
- Session table (last 20)
- Attempt table (last 30)
- CSV export for SPSS

### 2.2 API Endpoints

| Method | Endpoint | Request | Response |
|--------|----------|---------|----------|
| GET | `/api/health` | — | `{status, groq_key_configured}` |
| GET | `/api/questions?day=N&set=practice\|pretest\|posttest` | — | Array of question objects |
| POST | `/api/verify` | FormData: audio, reference, participant_id, question_id, attempt_num | `{passed, db_pass, stt_text, cosine_score, latency_ms, message}` |
| POST | `/api/verify-text` | FormData: text, reference, participant_id, question_id | `{passed, cosine_score, message}` |
| POST | `/api/session/complete` | JSON: participant_id, day, scores | `{status: "ok"}` |
| POST | `/api/test/submit` | JSON: participant_id, group_type, test_type, score, total | `{status: "ok"}` |
| GET | `/api/admin/export` | — | `{attempts, sessions, test_scores}` |
| GET | `/api/admin/metrics` | — | Feasibility metrics object |

### 2.3 Question Format

```json
{
  "id": "D1Q01",
  "stem": "The manager asked that all reports ______ submitted by Friday.",
  "options": ["are", "be", "were", "will be"],
  "correct_idx": 1,
  "explanation": "Use the subjunctive 'be' after 'asked that' in formal requests."
}
```

### 2.4 Question Distribution
- 30 practice questions, 10 per day, cycling every 3 days
- 30 pre-test questions (parallel form)
- 30 post-test questions (parallel form)

---

## 3. Pipeline Specification

### 3.1 Layer 1: dB Intensity Gate
- **Implementation:** Server-side numpy RMS → dB conversion
- **Formula:** `dB = 20 × log₁₀(RMS + 1e-9)` on int16 PCM samples
- **Threshold:** ≥ 60 dB (arbitrary scale relative to int16 range)
- **Note:** The frontend visual dB meter uses Web Audio API `getByteTimeDomainData` with +90 offset — these values DO NOT correlate with backend measurements. The frontend meter is for visual encouragement only.

### 3.2 Layer 2: Groq Whisper STT
- **Model:** `whisper-large-v3-turbo`
- **Language:** English (`language: "en"`)
- **Temperature:** 0.0 (deterministic)
- **Format:** WebM audio → Groq REST API → JSON response
- **Timeout:** 30 seconds
- **Fallback:** Raw PCM bytes auto-converted to WAV if no known header detected

### 3.3 Layer 3: Cosine Semantic Similarity
- **Model:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Threshold:** ≥ 0.80
- **Comparison:** STT output vs. reference explanation
- **Note:** Threshold is strict — punctuation/word-order variations can cause false negatives

### 3.4 Go/Modify Criteria (Table III)

| Metric | Go Criterion | Field |
|--------|-------------|-------|
| Session completion rate | ≥ 80% | `sessions.completed` |
| Attrition rate | ≤ 15% | Days < 12 |
| Mean round-trip latency | < 200 ms | `attempts.latency_ms` (includes Groq API) |
| dB gate pass rate | ≥ 85% | `attempts.db_pass` |
| Cosine score SD | < 0.05 | `attempts.cosine_score` |
| Bypass activation rate | ≤ 20% | `attempts.bypass_used` |

---

## 4. Database Schema

### 4.1 Table: attempts
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
participant_id TEXT,
group_type TEXT,
question_id TEXT,
attempt_num INTEGER,
db_pass INTEGER,        -- 0/1
stt_text TEXT,
cosine_score REAL,
passed INTEGER,          -- 0/1
bypass_used INTEGER,     -- 0/1
latency_ms INTEGER
```

### 4.2 Table: sessions
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT,
timestamp TEXT,
participant_id TEXT,
day INTEGER,
completed INTEGER,
score INTEGER,
total INTEGER
```

### 4.3 Table: test_scores
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT,
participant_id TEXT,
group_type TEXT,
test_type TEXT,         -- 'pretest' | 'posttest'
score INTEGER,
total INTEGER,
timestamp TEXT
```

---

## 5. GBL Mechanics

### 5.1 Scoring
- Correct answer (first try): +1
- Active recall voice success: +10
- Active recall bypass (typed): +5
- Total possible per session: 1×10 + 10×10 = 110 (Group B max)

### 5.2 Streak System
- 0: no indicator
- 1–3: ⚡
- 4–6: 🔥
- 7+: 🔥🔥

### 5.3 Visual Feedback
- Reward overlay animation (+1, +10, +5)
- Progress bar (question N/10)
- dB meter color: red < 60, green ≥ 60
- Option highlighting: green (correct), red (wrong), dim-green (reveal)

---

## 6. Deployment Configuration

### 6.1 Server
- Host: 5.78.177.52 (Hetzner VPS)
- Port: 8080 (internal), exposed via Cloudflare Tunnel
- Process: Uvicorn, single worker
- Venv: `/home/peter/toeic_pilot/venv/`

### 6.2 Cloudflare Tunnel
- URL: `https://gaming-attacked-byte-trance.trycloudflare.com`
- Created via: `cloudflared tunnel --url http://localhost:8080`
- Note: Temporary tunnel — expires on process restart

### 6.3 Nginx (External Access)
- nginx is available on port 80/443 but currently serves only mailscanner
- TOEIC app can be integrated via reverse proxy when sudo access is available
- Existing config: `/etc/nginx/sites-enabled/mailscanner`

---

## 7. Known Issues & Limitations

### 7.1 Critical
1. **dB meter mismatch:** Frontend visual dB ≠ backend measured dB — misleading to users
2. **Cosine threshold too strict:** 0.80 causes false negatives for paraphrased explanations

### 7.2 Moderate
3. **Safari incompatibility:** `audio/webm` MIME type not supported
4. **No Enter-key bypass submit:** Bypass input requires mouse click
5. **Last question button says "Next" not "Finish"**
6. **Record button says "Hold to Record" but is press-toggle, not hold**

### 7.3 Minor
7. **No audio playback:** User can't hear their own recording
8. **No page-unload warning:** Closing tab while recording loses data
9. **Small fonts on mobile** (1.1rem question, 0.95rem options)
10. **Bypass appears only after 2 fails** — some users may want it immediately

---

## 8. File Inventory

```
/home/peter/toeic_pilot/
├── venv/                          # Python virtual environment
├── data/
│   └── pilot.db                   # SQLite database (auto-created)
├── backend/
│   ├── main.py                    # FastAPI app (186 lines)
│   ├── pipeline.py                # 3-layer verification (151 lines)
│   ├── database.py                # SQLite CRUD + metrics (196 lines)
│   ├── questions.py               # 90 TOEIC questions (3 sets)
│   └── requirements.txt
└── frontend/
    ├── index.html                 # Login page
    ├── game.html                  # Main GBL game (501 lines)
    ├── test.html                  # Pre/post test
    ├── admin.html                 # Admin dashboard
    └── complete.html              # Session complete screen
```
