# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH team tournaments**. It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.13+ | Flask 3.0.0 | Vanilla JavaScript | In-memory state management
**Developed for:** Knights of Round Table - cEDH Team Championship tournaments

---

## Quick Start

```bash
# Install dependencies
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt

# Run the application
python tournament_dashboard.py

# Access dashboard
open http://127.0.0.1:5000
```

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
- **Win:** 5 points | **Draw:** 1 point | **Loss:** 0 points
- Team score = Sum of all 4 players' scores
- Finals winner determined by finals performance, Swiss as tiebreaker

---

## Architecture

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| **TournamentManager** | `tournament_dashboard.py` | Central state management, tournament lifecycle |
| **UnifiedSwissPairing** | `unified_swiss_pairing.py` | Constraint satisfaction solver for pod generation |
| **Frontend SPA** | `templates/dashboard_ultra_modern.html` | Single HTML file (~4,600 lines) with embedded CSS/JS |

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

### Finals
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate_semifinals_round` | POST | Generate Top 8 Cut (16-team only) |
| `/generate_finals` | POST | Generate Finals (top 4 teams) |
| `/standings` | GET | Current team standings |

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
├── tournament_dashboard.py          # Main Flask app (~3400 lines)
├── unified_swiss_pairing.py         # Pairing algorithm (~1800 lines)
├── templates/
│   └── dashboard_ultra_modern.html  # Frontend UI (~4600 lines)
├── test_tournament_comprehensive.py # Full tournament flow tests
├── test_score_correction.py         # Score editing tests
├── test_backup_restore.py           # Backup/restore tests
├── participants/
│   └── participant_team.xlsx        # Default Excel file path
├── venv/                            # Python virtual environment
├── requirements.txt                 # Python dependencies
└── CLAUDE.md                        # This file
```

---

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
