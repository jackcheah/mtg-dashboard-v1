# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH team tournaments**. It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.13+ | Flask 3.0.0 | Vanilla JavaScript | In-memory state management (with JSON persistence)
**Developed for:** Knights of Round Table - cEDH Team Championship tournaments

---

## Quick Start (Developer)

### 1. Setup Environment
```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Application
```bash
python tournament_dashboard.py
# Access at http://127.0.0.1:5001
```

### 3. Run E2E Tests
```bash
# Full simulation (server must be running)
python tests/e2e/simulate_full_tournament.py
```

<<<<<<< HEAD
**What this test does:**
1.  **Simulates User Actions**: Uses Playwright to click buttons, entering scores like a real user.
2.  **Verifies Mechanics**: Checks that tables load, rounds advance, and the Champion is declared.
3.  **Validates Logic**: Real-time verification of Swiss rules:
    *   **No Repeats**: Ensures players never face the same opponent twice in Swiss rounds.
    *   **Teammate Avoidance**: Ensures teammates are not paired together.
    *   **Champion**: Confirms the tournament reaches a conclusion.

---

## Tournament Structure

| Teams | Players | Swiss Rounds | Playoffs | Total Rounds |
|-------|---------|--------------|----------|--------------|
| 8     | 32      | 4            | Finals   | 5            |
| 12    | 48      | 4            | Finals   | 5            |
| 16    | 64      | 4            | Top 8 Cut + Finals | 6 |

### Scoring System

The tournament supports two scoring modes, selected after loading participants:

#### Western Mode (Default)
- **Win:** 5 points | **Draw:** 1 point | **Loss:** 0 points
- Players start with 0 points
- Team score = Sum of all 4 players' scores

#### Japanese Swiss Point Mode
- **Start:** Each player begins with 1000 points
- **Each round:** All players contribute 7% of their current points to a pool
- **Win:** Winner takes the entire pool (~280 pts in round 1)
- **Draw/Loss:** Players lose their 7% contribution
- Points accumulate across rounds (never reset)
- See `JAPANESE-IMPLEMENTATION.md` for full details

#### General Rules
- Finals winner determined by finals performance, Swiss as tiebreaker
- **Tiebreakers:** Best player score → Average player score → Early wins (exponentially weighted by round)

=======
>>>>>>> 9b5323584877a48f640347c2bfae5f205aff42b0
---

## Architecture

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| **TournamentManager** | `tournament_dashboard.py` | Central state management, tournament lifecycle, tiebreaker logic. Thread-safe. |
| **UnifiedSwissPairing** | `unified_swiss_pairing.py` | Constraint satisfaction solver for pod generation. |
| **Frontend SPA** | `templates/dashboard_ultra_modern.html` | Single HTML file (~5k lines) with embedded CSS/JS. Uses Custom Events for state changes. |
| **Projector View** | `templates/projector_view.html` | Read-only audience display with champion/MVP showcase. |

### Data Flow
1. **Load**: `load_participants()` reads Excel -> populates `TournamentManager` state.
2. **Setup**: `setup_tournament()` clears state, generates Round 1 (Random).
3. **Loop**: 
   - User submits scores (`/submit_player_results`).
   - `generate_swiss_round(N)` calculates pairings based on `player_scores` and `standings`.
   - State is auto-saved to `tournament_state.json.bak`.
4. **Finals**: `generate_finals()` or `generate_semifinals_round()` selects top teams based on tiebreakers.

### Backend Logic & Tiebreakers
Located in `TournamentManager` class:
- **`get_mvp(self)`**: Finds highest scorer in Top 4.
- **`get_team_tiebreaker_key`**: `(Total Score, Best Player, Avg Player, Early Wins)`.
- **`calculate_early_wins_score`**: Weighted sum (`R1*1000 + R2*100 ...`) to reward early dominance.

### Persistence Strategy
- **Format**: JSON serialization of `TournamentManager` dicts.
- **Rotation**: 4 files (`.bak`, `.bak.1`, `.bak.2`, `.bak.3`) to prevent corruption.
- **Auto-Restore**: On startup, checking for `.bak` files and loading the most recent valid one.

---

## Key Flask Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
<<<<<<< HEAD
| `/load_data` | POST | Load participants from Excel or sample data |
| `/set_scoring_mode` | POST | **Set scoring mode (western/japanese) before setup** |
| `/setup_tournament` | POST | Initialize tournament, generate Round 1 |
| `/setup_round/<N>` | POST | Generate round N |

### Score Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/submit_table_results` | POST | Submit scores for a table |
| `/submit_player_results` | POST | Finalize round scores |
| `/edit_table_results` | POST | **Edit previously submitted scores** |
| `/get_score_history/<round>/<table>` | GET | **View edit audit trail** |

### Tournament State
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/get_tournament_state` | GET | Full snapshot (standings, scores, submission status) |
| `/get_submission_status/<round>` | GET | Progress for a round |
| `/get_state_info` | GET | Current state and valid next actions |
| `/get_tables/<round>` | GET | Table assignments for a round |


### Backup & Monitoring (New!)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/save_backup` | POST | Manually trigger backup save |
| `/backup_health` | GET | Get backup health status (last success/failure, file info) |
| `/restore_backup` | POST | Restore tournament state from backup file |

### Finals & Display
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate_semifinals_round` | POST | Generate Top 8 Cut (16-team only) |
| `/generate_finals` | POST | Generate Finals (top 4 teams) |
| `/standings` | GET | Current team standings |
| `/final_standings` | GET | **Final standings with MVP calculation** |
=======
| `/setup_round/<N>` | POST | Generate pairing for round N. |
| `/submit_player_results` | POST | Main score submission handler. Recalculates team scores. |
| `/get_state_info` | GET | Polled by frontend. Returns current round, timer state, and valid actions. |
| `/backup_health` | GET | Returns status of background backup threads. |
| `/final_standings` | GET | Returns sorted lineup for Projector View (Leaderboard + MVP). |
>>>>>>> 9b5323584877a48f640347c2bfae5f205aff42b0

---

## Testing Guide (E2E)

The project relies on Playwright for verification.
- **Location**: `tests/e2e/`
- **Key Script**: `simulate_full_tournament.py` - Simulates a full 16-team run, verifying:
    - No repeat matchups.
    - No teammate pairings.
    - Correct Phase Transitions (Swiss -> Top8 -> Finals).
    - Champion declaration.

---

## File Structure

```
mtg-dashboard-v1/
├── tournament_dashboard.py          # Main Flask app 
├── unified_swiss_pairing.py         # Pairing algorithm 
├── templates/
│   ├── dashboard_ultra_modern.html  # Main UI
│   └── projector_view.html          # Projector UI
├── tests/
│   └── e2e/                         # Playwright test suite
├── participants/
│   └── participant_team.xlsx        # Participant data
├── requirements.txt                 # Dependencies
├── Dockerfile                       # Container config

├── CLAUDE.md                        # This file
└── README.md                        # User documentation
```

---

## Implementation Details: Swiss Pairing

**"Traditional Swiss"** implementation (in `unified_swiss_pairing.py`):
1.  **Group**: Sort teams by score into brackets.
2.  **Swap**: If repeats/conflicts exist in a bracket, swap lowest team with nearest neighbor.
3.  **Optimize**: Internal permutation search to minimize player-level repeats within the team matchup.
