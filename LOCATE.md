# TOEIC Active Recall Battle Game — Project Locator
# Last update: 2026-05-28

## Paths
PROJECT_ROOT=/home/peter/toeic_pilot
BACKEND=$PROJECT_ROOT/backend
FRONTEND=$PROJECT_ROOT/frontend
DATA=$PROJECT_ROOT/data
VENV=$PROJECT_ROOT/venv
GAME_HTML=$FRONTEND/game.html

## Start Server
cd $BACKEND && $VENV/bin/python main.py
# → http://localhost:8080

## Tunnel (public URL)
/tmp/cloudflared tunnel --url http://localhost:8080
# → https://conditional-bargains-soccer-standing.trycloudflare.com

## Game URL
https://conditional-bargains-soccer-standing.trycloudflare.com/static/game.html?pid=P001&group=B&day=1

## API Endpoints
GET  /api/questions?day=1&set=practice
POST /api/verify        (multipart: audio, reference, participant_id, question_id, attempt_num)
POST /api/verify-text   (multipart: text, reference, participant_id, question_id)
POST /api/session/complete (JSON: participant_id, day, scores)
GET  /api/health

## Tech Stack
- Backend: Python FastAPI + uvicorn
- STT: Groq whisper-large-v3
- NLP: sentence-transformers all-MiniLM-L6-v2 (cosine similarity)
- DB: SQLite (../data/pilot.db)
- Frontend: Single-page HTML + CYBERCORE CSS + RPG-Awesome + FoxyStoat pixel art

## Theme
- CYBERCORE CSS (cyberpunk 2077 neon — cdn.jsdelivr.net/npm/cybercore-css)
- RPG-Awesome icons (fantasy — cdn.jsdelivr.net/npm/rpg-awesome)
- FoxyStoat robot pixel art (box-shadow CSS, 1.6KB)
- Boss: "SYNTAX DRONE" → Phase 2 "OVERDRIVE MODE"

## Game Mechanics
- Group B: wrong answer → Battle Mode
- Phase 1: speak correct sentence, cosine ≥80%, 3 attempts, HP=3
- Phase 2: speak explanation, cosine ≥80%, 2 attempts → bypass typing
- VolMax ≥60% both phases
- Score: correct +10, battle win +5, bypass +5

## Quick Restart
kill $(ss -tlnp | grep 8080 | grep -oP 'pid=\K\d+') 2>/dev/null; sleep 2
cd /home/peter/toeic_pilot/backend && /home/peter/toeic_pilot/venv/bin/python main.py &

## Themes Tried (in /tmp/game-themes/)
1. RPGUI (RonenNess) — retro pixel, removed
2. Final-Fantasy-CSS (cafeTechne) — FF7 blue menu, replaced
3. CYBERCORE CSS (sebyx07) — CURRENT, cyberpunk neon
4. FoxyStoat/pixel-art — robot creature, CURRENT
