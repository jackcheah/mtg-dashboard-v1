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

```bash
# Run comprehensive 16-team test suite
source venv/bin/activate && python3 test_tournament_comprehensive.py --teams 16

# Run score correction tests
source venv/bin/activate && python3 test_score_correction.py

# Test all team configurations
python3 test_tournament_comprehensive.py --all
```

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
- Swiss-system pairing with zero repeat matchups
- Intelligent seating by player scores (Rounds 2+)
- Automatic next round generation
- Finals generation with Top 4 advancement
- Backup/restore functionality

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

**Last Updated:** 2025-12-17
**Status:** Production Ready (100% ready for local PC use)
