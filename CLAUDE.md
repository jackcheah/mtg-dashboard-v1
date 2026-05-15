# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH team tournaments**. It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.13+ | Flask 3.0+ | Vanilla JavaScript | In-memory state management (with JSON persistence)
**Developed for:** Knights of Round Table - cEDH Team Championship tournaments

---

## Quick Start (Developer)

### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Application
```bash
python tournament_dashboard.py
# Access at http://127.0.0.1:5001
# Projector: http://127.0.0.1:5001/projector
```

### 3. Optional: PIN Protection
```bash
TOURNAMENT_PIN=1234 python tournament_dashboard.py
# Score submission endpoints require X-Tournament-Pin header or pin in JSON body
```

### 4. Run Tests
```bash
pip install -r requirements-dev.txt
pytest tests/unit/ -v                                        # 21 unit tests
python tests/e2e/simulate_full_tournament.py --teams 8       # E2E (server must be running)
python tests/e2e/test_concurrent.py                          # Concurrent access tests
```

---

## Tournament Structure

| Teams | Players | Swiss Rounds | Playoffs | Total Rounds |
|-------|---------|--------------|----------|--------------|
| 8     | 32      | 4            | Finals   | 5            |
| 12    | 48      | 4            | Finals   | 5            |
| 16    | 64      | 4            | Top 8 Cut + Finals | 6 |

### Scoring
- **Win:** 5 points | **Draw:** 1 point | **Loss:** 0 points
- Valid outcomes per table: 1 winner + 3 losers, or 2-4 draws (no winner)
- Team score = Sum of all 4 players' scores
- **Tiebreakers:** Best player score -> Average player score -> Early wins (exponentially weighted by round)
- Finals winner determined by finals performance, Swiss as tiebreaker

---

## Architecture

### Core Components

| Component | File(s) | Description |
|-----------|---------|-------------|
| **TournamentManager** | `tournament_dashboard.py` | Central state management, tournament lifecycle, tiebreaker logic. Thread-safe with `@with_lock`. |
| **UnifiedSwissPairing** | `unified_swiss_pairing.py` | Constraint satisfaction solver for pod generation. Guarantees no-teammate pods. |
| **Dashboard UI** | `templates/dashboard_ultra_modern.html` + `static/css/dashboard.css` + `static/js/dashboard.js` | Split SPA: HTML template (271 lines) links to external CSS (3145 lines) and JS (2507 lines). |
| **Projector View** | `templates/projector_view.html` | Read-only audience display with adaptive polling and XSS-safe rendering. |

### Data Flow
1. **Load**: `load_participants()` reads Excel -> populates `TournamentManager` state.
2. **Setup**: `setup_tournament()` clears state, generates Round 1 (random seating).
3. **Swiss Loop**: Submit table scores -> Finalize round (with confirmation) -> Next round auto-generated based on standings.
4. **Playoffs**: Auto-generated after Swiss — Top 8 Cut (16-team only) then Finals (top 4 teams).
5. **Champion**: Determined by finals performance (primary) with Swiss+Top8 as tiebreaker.

### Key Backend Logic
- **`_handle_round_transition()`**: Shared helper for round finalization — generates next round, finals, or determines winner. Includes recovery if generation fails.
- **`calculate_early_wins_score()`**: Dynamic weights based on `swiss_rounds_count`, reads from `table_submissions`.
- **`get_mvp()`**: Highest individual scorer among Top 4 teams only.
- **Score validation**: Max 1 winner per table; all 4 players must be scored; win cannot coexist with draw.
- **Round finalization**: Requires ALL tables submitted before round can be finalized.

### Persistence
- **Format**: JSON serialization including `swiss_round_scores`, `top8_cut_scores`, `final_round_scores`.
- **Rotation**: 4 backup files (`.bak`, `.bak.1`, `.bak.2`, `.bak.3`).
- **Auto-Restore**: Tries primary then numbered backups in order. Rehydrates pairing engine constraints by replaying round history.

---

## Key Flask Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/load_data` | POST | Load participants from Excel or sample data |
| `/setup_tournament` | POST | Initialize tournament, generate Round 1 |
| `/submit_table_results` | POST | Submit scores for a specific table (PIN-protected) |
| `/submit_player_results` | POST | Finalize round, trigger next round generation |
| `/edit_table_results` | POST | Edit previously submitted scores (before finalization) |
| `/revert_table_submission` | POST | Undo a table submission before finalization |
| `/get_state_info` | GET | Current state and valid next actions |
| `/get_tournament_state` | GET | Full snapshot (standings, scores, submission status) |
| `/get_submission_status/<round>` | GET | Per-round submission progress |
| `/save_backup` | POST | Manually trigger backup save |
| `/restore_backup` | POST | Restore tournament state from backup |
| `/final_standings` | GET | Final standings with MVP calculation |
| `/export/standings` | GET | Download standings as CSV |

---

## Testing

### Unit Tests (21 tests)
```bash
pytest tests/unit/ -v
```
Covers: tiebreaker logic, final standings, MVP, state machine, backup/restore integrity, score validation (illegal combos, incomplete tables, incomplete round finalization).

### E2E Tests
```bash
python tests/e2e/simulate_full_tournament.py --teams [8|12|16]
```
Full Playwright simulation: setup -> Swiss -> playoffs -> champion. Uses dynamic waits (not hardcoded sleeps). Returns exit code 1 on failure.

### Concurrent Tests
```bash
python tests/e2e/test_concurrent.py
```
Thread-safety verification: concurrent table submissions, double finalization rejection, submit-during-edit.

---

## File Structure

```
mtg-dashboard-v1/
├── tournament_dashboard.py          # Main Flask app + TournamentManager
├── unified_swiss_pairing.py         # Pairing algorithm
├── static/
│   ├── css/dashboard.css            # Dashboard styles (3145 lines)
│   └── js/dashboard.js              # Dashboard logic (2507 lines)
├── templates/
│   ├── dashboard_ultra_modern.html  # Dashboard HTML shell (271 lines)
│   └── projector_view.html          # Projector display
├── tests/
│   ├── unit/
│   │   └── test_tournament_manager.py  # 21 pytest unit tests
│   └── e2e/
│       ├── simulate_full_tournament.py # Playwright E2E
│       ├── test_concurrent.py          # Concurrent access tests
│       └── generate_teams.py           # Test data generator
├── participants/
│   └── participant_team.xlsx        # Participant data
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Dev/test dependencies
├── CLAUDE.md                        # This file
└── README.md                        # User documentation
```

---

## Swiss Pairing Implementation

**"Traditional Swiss"** in `unified_swiss_pairing.py`:
1. **Group**: Sort teams by score into brackets of 4.
2. **Swap**: If repeats/conflicts exist in a bracket, swap lowest team with nearest neighbor.
3. **Optimize**: Permutation search to minimize player-level repeats within team matchups.
4. **Guarantees**: No teammates in same pod. Zero repeat matchups for 16 teams / 4 rounds. Minimized repeats for 8/12 teams (mathematically impossible to eliminate all).
