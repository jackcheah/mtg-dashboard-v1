# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH tournaments**. It supports both **team events** (4 players per team) and **individual events** (solo players). It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.13+ | Flask 3.0+ | Vanilla JavaScript | In-memory state management (with JSON persistence)
**Developed for:** Knights of Round Table - cEDH Championship tournaments

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
pytest tests/unit/ -v                                        # 131 unit tests
python tests/e2e/simulate_full_tournament.py --teams 8       # E2E (server must be running)
python tests/e2e/test_concurrent.py                          # Concurrent access tests
```

---

## Event Modes

The system supports two event modes, selected before loading participants:

### Team Mode (default)
- 4 players per team, 8/12/16 teams
- Team standings (sum of player scores)
- No teammates in same pod (hard constraint)
- Tiebreakers: Team score → Best player → Average → Early wins

### Individual Mode
- 16+ solo players (any count)
- Individual standings (player scores directly)
- Avoid repeat opponents (soft constraint via optimization)
- Supports non-multiple-of-4 counts: 3-player pods and bye system
- Player Drop feature: TO can remove players between rounds
- Tiebreakers: Score → Early wins

---

## Tournament Structure

### Team Mode

| Teams | Players | Swiss Rounds | Playoffs | Total Rounds |
|-------|---------|--------------|----------|--------------|
| 8     | 32      | 4            | Finals   | 5            |
| 12    | 48      | 4            | Finals   | 5            |
| 16    | 64      | 4            | Top 8 Cut + Finals | 6 |

### Individual Mode

| Players | Swiss Rounds | Playoffs | Total Rounds |
|---------|--------------|----------|--------------|
| ≤16     | 4            | Finals (top 4) | 5 |
| 17+     | 4            | Top Cut (top 10) + Finals (top 4) | 6 |

### Scoring Modes (both apply to Team and Individual)
- **Western:** Win=5, Draw=1, Loss=0. Start at 0 points.
- **Japanese:** Start at 1000 points. Each round: 7% contributed to pool. Winner takes pool. Losers/draws lose their contribution.

### Score Validation
- **4-player pods:** 1 winner + 3 losers, OR 2-4 draws + rest losers (no winner)
- **3-player pods (individual mode):** 1 winner + 2 losers, OR 3 draws, OR 2 draws + 1 loser
- **Bye players:** 1-2 remainder players get automatic win (5pts Western, no change Japanese)

---

## Architecture

### Core Components

| Component | File(s) | Description |
|-----------|---------|-------------|
| **TournamentManager** | `tournament_dashboard.py` | Central state management, tournament lifecycle, scoring, finals. Thread-safe with `@with_lock`. |
| **UnifiedSwissPairing** | `unified_swiss_pairing.py` | Constraint satisfaction solver. Team mode: no-teammate pods. Individual mode: score-sorted grouping with repeat-avoidance. |
| **Dashboard UI** | `templates/dashboard_ultra_modern.html` + `static/css/dashboard.css` + `static/js/dashboard.js` | Split SPA with modals for event/scoring mode selection. |
| **Projector View** | `templates/projector_view.html` | Read-only audience display with adaptive polling. |

### Key Enums
- **`EventMode`**: TEAM | INDIVIDUAL
- **`ScoringMode`**: WESTERN | JAPANESE
- **`TournamentState`**: INITIAL → PARTICIPANTS_LOADED → TOURNAMENT_SETUP → SWISS_IN_PROGRESS → TOP8_IN_PROGRESS → FINALS_IN_PROGRESS → FINALS_COMPLETE

### Data Flow
1. **Configure**: Select Event Mode (team/individual) → Select Scoring Mode (western/japanese).
2. **Load**: `load_participants()` reads Excel → populates state. If no file found, operator must explicitly opt into sample data (DEMO MODE banner shown). Individual mode: each player becomes a synthetic "team of 1". Duplicate player names auto-disambiguated.
3. **Setup**: `setup_tournament()` validates, initializes scores, generates Round 1.
4. **Swiss Loop**: Submit table scores → (Optional: Drop players) → Finalize round → Next round auto-generated.
5. **Playoffs**: Top Cut (if applicable) → Finals. Individual mode: Top 10 cut (top 2 get byes, 8 play), then top 4 finals.
6. **Champion**: Determined by finals performance (primary) with earlier rounds as tiebreaker.
7. **Reset**: At any point, operator can reset tournament (requires typing "RESET" to confirm). Backup files preserved for potential restore.

### Key Backend Logic
- **`_handle_round_transition()`**: Routes to correct next phase based on event mode and round number.
- **`generate_swiss_round()`**: Creates/rebuilds `UnifiedSwissPairing` engine, handles bye allocation for individual mode.
- **`drop_player()`**: Individual mode only. Removes player from active structures, forces pairing engine rebuild.
- **`_generate_round_individual_mode()`**: Score-sorted Swiss pairing for individuals with swap optimization.
- **Score validation**: Pod-size-aware (3 or 4 players), mode-aware (team vs individual).

### Persistence
- **Format**: JSON with `event_mode`, `scoring_mode`, `dropped_players`, `bye_players`, round results.
- **Rotation**: 4 backup files (`.bak`, `.bak.1`, `.bak.2`, `.bak.3`).
- **Rehydration**: Restores pairing engine by replaying round history and constraint tracking.

---

## Key Flask Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/set_event_mode` | POST | Set event mode (team/individual) — must be INITIAL state |
| `/set_scoring_mode` | POST | Set scoring mode (western/japanese) — before setup |
| `/load_data` | POST | Load participants from Excel. Returns `offer_sample: true` if file missing (sample data requires explicit opt-in via `use_sample_data: true`) |
| `/setup_tournament` | POST | Initialize tournament, generate Round 1 |
| `/submit_table_results` | POST | Submit scores for a specific table (PIN-protected) |
| `/submit_player_results` | POST | Finalize round, trigger next round generation |
| `/drop_player` | POST | Drop a player from individual event (between rounds) |
| `/edit_table_results` | POST | Edit previously submitted scores (before finalization) |
| `/revert_table_submission` | POST | Undo a table submission before finalization |
| `/reset_tournament` | POST | Full reset to INITIAL state. Requires `{"confirm": "RESET"}` body. Backup files preserved |
| `/get_state_info` | GET | Current state and valid next actions |
| `/get_tournament_state` | GET | Full snapshot (standings, scores, event_mode, dropped_players) |
| `/get_submission_status/<round>` | GET | Per-round submission progress |
| `/save_backup` | POST | Manually trigger backup save |
| `/restore_backup` | POST | Restore tournament state from backup |
| `/final_standings` | GET | Final standings with MVP calculation |
| `/export/standings` | GET | Download standings as CSV |

---

## Individual Mode Specifics

### Bye System
- When player count is not divisible by 4:
  - Remainder 3: Last 3 players form a 3-player pod (all play)
  - Remainder 1-2: Bottom-ranked players get byes (automatic win)
- Bye = 5pts (Western) or no change (Japanese)

### Player Drop
- Available only in individual mode, during Swiss rounds
- Timing: After all tables submit, before round finalization
- Effect: Player removed from future pairings, score frozen, still appears in final standings
- Pairing engine rebuilt for next round to reflect reduced player count

### Top Cut (>16 players)
- Top 10 players advance after Swiss
- Top 2 seeds receive byes
- Remaining 8 play in 2 tables of 4
- Top 4 then advance to Finals (1 table)

---

## Testing

### Unit Tests (131 tests)
```bash
pytest tests/unit/ -v
```
Covers: tiebreaker logic, final standings, MVP, state machine, backup/restore integrity, score validation, reset confirmation, individual mode.

### E2E Tests
```bash
python tests/e2e/simulate_full_tournament.py --teams [8|12|16]
```
Full simulation: setup → Swiss → playoffs → champion.

### Concurrent Tests
```bash
python tests/e2e/test_concurrent.py
```
Thread-safety: concurrent submissions, double finalization rejection.

---

## File Structure

```
mtg-dashboard-v1/
├── tournament_dashboard.py          # Main Flask app + TournamentManager
├── unified_swiss_pairing.py         # Pairing algorithm (team + individual modes)
├── static/
│   ├── css/dashboard.css            # Dashboard styles
│   └── js/dashboard.js              # Dashboard logic (event mode, scoring, drops)
├── templates/
│   ├── dashboard_ultra_modern.html  # Dashboard HTML (event/scoring mode modals)
│   └── projector_view.html          # Projector display
├── tests/
│   ├── unit/
│   │   └── test_tournament_manager.py  # pytest unit tests
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

### Team Mode (`unified_swiss_pairing.py`)
1. **Group**: Sort teams by score into brackets of 4.
2. **Swap**: If repeats/conflicts exist, swap lowest team with nearest neighbor.
3. **Optimize**: Permutation search to minimize player-level repeats.
4. **Guarantees**: No teammates in same pod. Zero repeat matchups for 16 teams / 4 rounds.

### Individual Mode (`_generate_round_individual_mode()`)
1. **Sort**: All players sorted by score (descending).
2. **Chunk**: Group into pods of 4 (bottom remainder gets byes or forms 3-player pod).
3. **Optimize**: Swap players between adjacent pods to minimize repeat opponents.
4. **Engine rebuild**: After player drops, engine is recreated with reduced player list.
