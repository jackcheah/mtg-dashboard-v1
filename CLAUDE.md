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

### Tournament State Machine

```
INITIAL → PARTICIPANTS_LOADED → TOURNAMENT_SETUP → SWISS_IN_PROGRESS → SWISS_COMPLETE
                                                                            ↓
                                    FINALS_COMPLETE ← FINALS_IN_PROGRESS ← TOP8_COMPLETE (16-team)
```

**State transitions happen automatically** based on user actions. Endpoints are protected with `@require_state` decorator.

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

### Phase 3: UX & Error Handling ✅
- **Task 3.1:** Table submission status tracking with progress bar
- **Task 3.2:** Score correction mechanism with audit trail
- **Task 3.3:** Enhanced error messages with user-friendly suggestions
- **Task 3.4:** Tournament state machine with `@require_state` decorator

---

## Critical Design Decisions

### Incremental Round Generation
Rounds generated one at a time after previous round submission. Ensures fair seeding based on current standings.

### Intelligent Seating
- **Round 1:** Randomized
- **Rounds 2+:** Players sorted by `player_scores[]` within each pod
- Highest scorer → Seat 1 (players of similar strength face each other)

### Constraint Solver
1. **Primary:** Constraint satisfaction with backtracking (500K node limit)
2. **Fallback:** Dynamic pairing with relaxed constraints
3. **Hard Constraint:** Teammates NEVER together (never relaxed)

### Score Correction Audit Trail
All score edits are tracked with timestamp, previous values, new values, and reason. View history via `/get_score_history` endpoint or history badge in UI.

---

## Common Pitfalls

1. **Team vs Player Scores**: Both tracked separately. `scores[team]` = aggregate of `player_scores[]` for all 4 members.

2. **Round State**: Use `submitted_rounds` set to prevent double-submission. Check `if round_num in self.submitted_rounds`.

3. **Seating is Applied Post-Generation**: Constraint solver generates unordered pods. Seating logic runs in `apply_intelligent_seating()`.

4. **Max Rounds is Dynamic**: Use `if round_num == self.max_rounds`, never hardcode round numbers.

5. **Excel Path**: Default is `participants/participant_team.xlsx`. Search for this string to change.

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

## Testing Status

| Test Suite | Tests | Status |
|------------|-------|--------|
| 16-Team Tournament Flow | 37 | ✅ All Pass |
| 8-Team Tournament Flow | 28 | ✅ All Pass |
| Score Correction (Task 3.2) | 18 | ✅ All Pass |
| Backup/Restore | 3 | ✅ All Pass |

### Run All Tests
```bash
source venv/bin/activate
python3 test_tournament_comprehensive.py --all
python3 test_score_correction.py
```

---

## Known Limitations

| Limitation | Workaround |
|------------|------------|
| Single tournament per server | Restart server between tournaments |
| In-memory only (no database) | Use backup/restore for persistence |
| Local-only by default | Change to `host='0.0.0.0'` for network |
| Manual score entry | No external API integration |

---

## Deployment

### Production Configuration
```python
# In tournament_dashboard.py, last line:
app.run(host='0.0.0.0', port=5000, debug=False)
```

### Requirements
- Python 3.13+
- Flask 3.0.0
- openpyxl (Excel import)
- Modern web browser

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-12-15 | Phase 2+3 complete, score correction, state machine |
| 1.0 | 2024-12 | Initial release, core tournament flow |

**Last Updated:** 2025-12-15  
**Status:** Production Ready
