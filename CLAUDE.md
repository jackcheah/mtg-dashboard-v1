# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH team tournaments**. It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.13+ | Flask 3.0.0 | Vanilla JavaScript | In-memory state management
**Developed for:** Knights of Round Table - cEDH Team Championship tournaments

---

## Quick Start

### 1. First Time Setup
```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

# Install dependencies (only do this when requirements change)
pip install -r requirements.txt
```

### 2. Daily Workflow
```bash
# 1. Activate environment (Required for every new terminal)
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 2. Run application
python tournament_dashboard.py
```

# Access dashboard
open http://127.0.0.1:5001

### Testing

The project now relies on a comprehensive **End-to-End (E2E) Simulation** to verify tournament logic, including the sophisticated Swiss Pairing system.

```bash
# Run the Full Tournament Simulation (16 Teams)
python tests/e2e/simulate_tournament_flow.py
```

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

---

## Architecture

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| **TournamentManager** | `tournament_dashboard.py` | Central state management, tournament lifecycle, tiebreaker logic |
| **UnifiedSwissPairing** | `unified_swiss_pairing.py` | Constraint satisfaction solver for pod generation |
| **Frontend SPA** | `templates/dashboard_ultra_modern.html` | Single HTML file (~5,530 lines) with embedded CSS/JS |
| **Projector View** | `templates/projector_view.html` | Read-only audience display with champion/MVP showcase (~800 lines) |

### Frontend Architecture (UX Overhaul)
- **Vanilla JS**: No framework overhead. Classes (`ModalManager`, `KeyboardNavigator`) used for organization.
- **CSS Variables**: Extensive use of `--color-primary`, `--spacing-md` for consistent theming.
- **Glassmorphism**: Backdrop filters and semi-transparent backgrounds for modern aesthetic.
- **localStorage**: Client-side persistence for user preferences (e.g., Compact Mode).

### Data Flow

```
Excel/Sample Data → load_participants() → TournamentManager state
                                          ↓
                                   setup_tournament()
                                   - Reset scores
                                   - Generate Round 1 (random pairing/seating)
                                          ↓
                              User submits scores via frontend
                                          ↓
                              submit_player_results()
                              - Update player_scores[]
                              - Recalculate team scores
                                          ↓
                              generate_swiss_round(N)
                              - Swiss pairing by team standings
                              - Intelligent seating by player_scores[]
                              - Constraints: no teammates, no repeat matchups
                                          ↓
                              After final Swiss → generate_finals()
                              - Top 4 teams advance
                              - Champion determined
```

---

## Key Flask Endpoints

### Tournament Setup
| Endpoint | Method | Description |
|----------|--------|-------------|
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

---

## Key Backend Methods

### Tiebreaker System (TournamentManager)

**`get_mvp(self)`** (Line ~1208)
- Finds highest individual scorer among Top 4 teams
- Returns dict: `{player_name, team_name, total_score}`
- Used by `/final_standings` endpoint for projector display

**`get_team_tiebreaker_key(team_name, total_score)`** (Line ~1260)
- Returns tuple for lexicographic sorting: `(total_score, best_player_score, avg_player_score, early_wins_score)`
- Used by `generate_semifinals_round()` and `generate_unified_finals()`
- Ensures consistent tiebreaker application across all advancement decisions

**`calculate_early_wins_score(team_name)`** (Line ~1293)
- Calculates weighted score based on round timing
- Formula: `Round1_pts × 1000 + Round2_pts × 100 + Round3_pts × 10 + Round4_pts × 1`
- Example: 2 wins in Round 1 (10 pts × 1000 = 10,000) beats 2 wins in Round 2 (10 pts × 100 = 1,000)
- Rewards consistent early performance over late surge

---

## Comprehensive Testing Guide (E2E)

The project uses a sophisticated Playwright-based simulation suite to verify the complex tournament logic.

### 1. Test Scripts (`tests/e2e/`)

| Script | Purpose | Recommended For |
|--------|---------|-----------------|
| `simulate_full_tournament.py` | **Full Verification**. Tracks every player/team through 6 rounds. Checks Swiss pairings, Top 8 logic, and Finals. Generates `tournament_test_report.json`. | **Pre-Release Validation** |
| `simulate_tournament_flow.py` | **Basic Check**. Quick run-through of the flow without deep tracking. | **Quick Sanity Check** |
| `generate_16_teams.py` | **Data Gen**. Creates `participant_team.xlsx` with 16 teams (64 players). | **Test Setup** |

### 2. Running the Full Simulation
1.  **Start Server**: `python tournament_dashboard.py`
2.  **Run Test**: `python tests/e2e/simulate_full_tournament.py`

### 3. What It Validates
*   **Swiss Logic**: Checks 0 repeat matchups and 0 teammate pairings in Swiss rounds.
*   **Phase Transitions**: Verifies correct advancement from Swiss -> Top 8 -> Finals.
*   **Champion**: Ensures a winner is declared.
*   **Backup System**: Verifies "Save Backup" button works at critical stages.

---

## Architecture Deep Dive: Backup & Recovery

The system was hardened for 12-hour production stability (Jan 2026).

### 1. Persistence Layer
*   **Format**: JSON serialization of the `TournamentManager` state.
*   **Location**: Root directory (`tournament_state.json.bak`).
*   **Frequency**:
    *   **Automatic**: Every 5 minutes (via background daemon thread).
    *   **Triggered**: On every critical state change (Setup, Score Submit, Round Gen).
    *   **Manual**: User-initiated via UI button.

### 2. Rotation Strategy (3-Level Redundancy)
To prevent data corruption during write operations, we maintain 4 files:
1.  `tournament_state.json.bak`: Latest successful save.
2.  `tournament_state.json.bak.1`: Previous save (-1).
3.  `tournament_state.json.bak.2`: Save before that (-2).
4.  `tournament_state.json.bak.3`: Oldest version (-3).

### 3. Crash Recovery
*   **Mechanism**: On startup, `TournamentManager` checks for `.bak` files.
*   **Process**:
    1.  Loads state into memory.
    2.  Restores all objects (players, teams, pairings, scores).
    3.  **Timer Restoration**: Restores `timer_start_time` and `elapsed` so the clock resumes correctly.
    4.  Frontend automatically syncs with backend state on page load.

### 4. Monitoring
*   **Endpoint**: `/backup_health` returns JSON status (last success, failures, file size).
*   **Frontend**: UI polls this endpoint to detect silent backup failures (e.g., disk full).

---

## Features Implemented

### Phase 1: Core Tournament Flow ✅
- **Traditional Swiss Pairing**: Implemented with a 3-Layer Logic (Score -> Swap -> Optimize).
- **Intelligent Seating**: Players seated by individual score (Rounds 2+).
- **Automatic Round Generation**: Incremental generation based on previous results.
- **Finals Generation**: Top 4 advancement (or Top 8 Cut -> Finals for 16 teams).

### Phase 2: Security & Validation ✅
- XSS vulnerability prevention (data attributes, event delegation)
- Comprehensive input validation on all endpoints
- Double-submission prevention (backend tracking + frontend disable)

### Phase 3: UX (Dec 2025 Overhaul) ✅
- **Visuals**: "Ultra Modern" glassmorphism UI, Sticky Header, Dynamic Timer.
- **Efficiency**: "Auto-fill losers" (75% click reduction), "Batch Submit".
- **Accessibility**: Full keyboard navigation (`Tab`, `1/2/3`, `Ctrl+Enter`) and `?` help overlay.
- **Feedback**: Stacked toasts, custom non-blocking modals (no use of `window.confirm`).

### Phase 4: Production Hardening (Jan 2026) ✅
- **Thread Safety**: All state-modifying endpoints protected with locks for concurrent access
- **Automatic Backups**: Background thread saves state every 5 minutes
- **Backup Rotation**: 4-level rotation system (current + 3 historical backups)
- **Timer Persistence**: Timer state saved/restored across server restarts
- **Backup Health Monitoring**: /backup_health endpoint for real-time status
- **Manual Backup Button**: "Save Backup" button available throughout entire tournament (setup, Swiss rounds, Top 8 Cut, Finals)
- **Crash Recovery**: Automatic state restoration on server startup
- **Improved Error Handling**: Specific exception types with detailed logging

### Phase 5: Projector Enhancements & Tiebreakers (Jan 2026) ✅
- **Projector View Enhancement**: Horizontal split layout (champion left, finalists + MVP right)
- **Visual Score Hierarchy**: Final scores (★★★) > Top Cut (★★) > Swiss (★) with size/color differentiation
- **MVP Calculation**: Highest individual scorer from Top 4 teams displayed on projector
- **Comprehensive Tiebreakers**: 4-level system (Total → Best Player → Average → Early Wins)
- **Early Wins Weighting**: Exponential time advantage (Round 1: 1000x, Round 2: 100x, Round 3: 10x, Round 4: 1x)

---

## Verification & Troubleshooting

### Manual Verification Checklist
- [ ] **Load**: "Load Participants" loads data correctly (8/12/16 teams).
- [ ] **Setup**: "Setup Tournament" generates Round 1 pairings.
- [ ] **Scoring**: "Win" auto-fills 3 "Losses"; "Submit Table" saves/dims card.
- [ ] **Batch**: "Batch Submit" submits all fully-scored tables.
- [ ] **UX**: Sticky header visible; Compact Mode toggles/persists; `?` shows keys.
- [ ] **Finals**: Transition to Top 8/Finals works correctly.

### Common Pitfalls & Troubleshooting
1. **"Round 2 Not Generating"**: Check for undimmed tables. Use "Batch Submit" to catch stragglers.
2. **"Mismatched State"**: If server restarts, refresh page -> "Load Participants" -> "Setup Tournament" to recover state from backup.
3. **Team vs Player Scores**: Tracked separately. `scores[team]` is aggregate of members.
4. **Excel Path**: Defaults to `participants/participant_team.xlsx`.
5. **Score Zero?**: Refresh page to reload from backend state.

---

## File Structure

```
mtg-dashboard-v1/
├── tournament_dashboard.py          # Main Flask app (~4000 lines)
├── unified_swiss_pairing.py         # Pairing algorithm (~2370 lines)
├── templates/
│   ├── dashboard_ultra_modern.html  # Frontend UI (~5530 lines)
│   └── projector_view.html          # Projector display (~700 lines)
├── tests/
│   └── e2e/                         # End-to-End test suite
│       ├── README.md                # E2E test documentation
│       ├── simulate_tournament_flow.py   # Basic E2E simulation
│       ├── simulate_full_tournament.py   # Comprehensive E2E with tracking
│       └── generate_16_teams.py          # Test data generator
├── participants/
│   └── participant_team.xlsx        # Default Excel file path
├── requirements.txt                 # Python dependencies (Flask, openpyxl)
├── Dockerfile                       # Docker container configuration
├── docker-compose.yml               # Docker Compose setup
├── TOURNAMENT_SCORING_SYSTEM.md     # Detailed scoring documentation
├── BACKUP-PLAN.md                   # 12-hour production readiness plan
├── PHASE1-IMPLEMENTATION-SUMMARY.md # Phase 1 critical fixes documentation
├── PHASE2-IMPLEMENTATION-SUMMARY.md # Phase 2 high priority fixes documentation
├── PHASE5-IMPLEMENTATION-SUMMARY.md # Phase 5 projector enhancements & tiebreakers
├── CLAUDE.md                        # This file
└── README.md                        # User documentation
```

---

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or use the convenience scripts
./build-and-run.sh    # Mac/Linux
.\build-and-run.bat   # Windows
```

The container exposes port 5001 and uses Werkzeug production mode.

---

## Technical Deep Dive: Traditional Swiss Implementation

We have implemented a **Traditional Swiss Pairing** system that prioritizes score-based pairing while maintaining strict avoidance of repeat matchups.

### The 3-Layer Pairing Strategy

**Layer 1: Score-Based Grouping**
*   Teams are sorted by score and grouped into brackets of 4 (e.g., Rank 1-4, Rank 5-8).
*   **Goal**: Winners play Winners.

**Layer 2: Intelligent Team Swapping**
*   If a team-level repeat is detected (e.g., Team A and Team B in the same bracket played before):
*   **Action**: The system identifies the lowest-ranked problem team and swaps it with a team from an adjacent bracket.
*   **Priority**: Minimize score disruption (swap with nearest neighbor).

**Layer 3: Exhaustive Player Optimization**
*   If team-levels repeats are unavoidable (rare, but possible in small events):
*   **Action**: The system uses an exhaustive permutation search (up to 13,824 combinations) to assign players within the pod.
*   **Goal**: Minimize player-level repeat matchups even if teams are meeting again.

### Rollback Configuration
To revert to the legacy "Pod Consistency" algorithm (which prioritizes no repeats over score brackets):
```python
# In tournament_dashboard.py
use_traditional_swiss=False
```
