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
| `/setup_round/<N>` | POST | Generate pairing for round N. |
| `/submit_player_results` | POST | Main score submission handler. Recalculates team scores. |
| `/get_state_info` | GET | Polled by frontend. Returns current round, timer state, and valid actions. |
| `/backup_health` | GET | Returns status of background backup threads. |
| `/final_standings` | GET | Returns sorted lineup for Projector View (Leaderboard + MVP). |

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
