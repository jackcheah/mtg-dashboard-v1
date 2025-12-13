# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a web-based tournament management system for Magic: The Gathering cEDH team tournaments. It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.8+ | Flask 3.0.0 | Vanilla JavaScript | In-memory state management

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python tournament_dashboard.py

# Access dashboard at http://127.0.0.1:5000
```

### Testing
```bash
# Run comprehensive test suite (8, 12, or 16 teams)
python test_tournament_comprehensive.py --teams 16 --verbose

# Test specific team count
python test_tournament_comprehensive.py --teams 8
python test_tournament_comprehensive.py --teams 12

# Manual testing workflow:
# 1. Load Participants → 2. Setup Tournament → 3. Submit rounds → 4. Verify finals
```

## Architecture

### Core Components

**1. TournamentManager** ([tournament_dashboard.py:11-2831](tournament_dashboard.py))
- Central state management class handling tournament lifecycle
- Key state: `participants`, `teams`, `scores`, `player_scores`, `tables`, `submitted_rounds`
- Manages incremental round generation (Round 1 on setup, subsequent rounds after prior submission)

**2. UnifiedSwissPairing** ([unified_swiss_pairing.py:415+](unified_swiss_pairing.py))
- Constraint satisfaction solver for pod generation
- Enforces: teammates never together (hard), zero repeat matchups (soft)
- Uses HybridConstraintSolver with backtracking (500K node limit)

**3. Frontend SPA** ([templates/dashboard_ultra_modern.html](templates/dashboard_ultra_modern.html))
- Single HTML file with embedded CSS/JS (~3,900 lines)
- Glassmorphism design with purple/cyan color scheme
- Direct fetch() calls to Flask REST endpoints

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
                              - Apply constraints (no teammates, no repeats)
                                          ↓
                              After final Swiss round → generate_finals()
                              - Top 4 teams advance
                              - Winner determined by finals + Swiss tiebreaker
```

### Critical Design Decisions

**Incremental Round Generation**
- Rounds generated one at a time after previous round submission
- Ensures fair seeding based on current standings
- Round 1: random pairing and seating
- Rounds 2+: Swiss pairing by team scores, seating by individual player scores

**Intelligent Seating** ([tournament_dashboard.py:783-836](tournament_dashboard.py#L783-L836))
- Round 1: Randomized
- Rounds 2+: Players sorted by `player_scores[]` within each pod
- Highest scorer → Seat 1 (players of similar strength face each other)

**In-Memory State Management**
- No database or persistence layer
- State lost on server restart
- Backup/restore feature exists but is disabled due to bugs
- Single tournament per Flask instance

**Tournament Structure**
- 8 teams → 4 Swiss rounds + Finals (5 total)
- 12 teams → 4 Swiss rounds + Finals (5 total)
- 16 teams → 4 Swiss rounds + Top 8 Cut + Finals (6 total)
- Configurable: 4 or 5 Swiss rounds via frontend

## Important Implementation Details

### Scoring System
- **Individual:** Win = 5 points, Draw = 1 point, Loss = 0 points
- **Team Score:** Sum of all 4 players' scores per round
- Both `player_scores[]` and `scores[]` tracked separately and must stay synchronized

### Constraint Solver Approach
1. **Primary:** Constraint satisfaction with backtracking (HybridConstraintSolver)
2. **Fallback:** Dynamic pairing with relaxed constraints
3. **Last Resort:** Allow repeat matchups if necessary

The solver tries three strategies in order. Teammates constraint is NEVER relaxed.

### Round Numbering
- 1-based indexing: `current_round=1` is the first round
- `tables[1]` contains Round 1 pairings
- Max rounds varies: 5 for 8/12 teams, 6 for 16 teams
- Always check `round_num == tournament.max_rounds`, never hardcode round 5

### Excel Import
- Default path: `participants/participant_team.xlsx` (configured in Flask route)
- Supports column-based (team names as headers) or row-based format
- Validation: exactly 4 players per team, total teams must be 8/12/16
- Fallback: `create_sample_data()` generates 8 teams if Excel missing ([tournament_dashboard.py:380](tournament_dashboard.py#L380))

### Tournament State Machine (Phase 3.4)

**State Lifecycle:**
```
INITIAL → load_data → PARTICIPANTS_LOADED → setup_tournament → TOURNAMENT_SETUP
  → submit_table (Round 1) → SWISS_IN_PROGRESS → submit_table (all Swiss) → SWISS_COMPLETE
  → generate_top8 (16-team) → TOP8_IN_PROGRESS → TOP8_COMPLETE
  → generate_finals → FINALS_IN_PROGRESS → submit_table (finals) → FINALS_COMPLETE
```

**State Validation:**
- Endpoints are protected with `@require_state` decorator
- Prevents out-of-sequence operations (e.g., submitting scores before setup)
- State transitions happen automatically based on actions
- Use `GET /get_state_info` to check current state and valid next actions

### Key Flask Endpoints
- `POST /load_data` - Load participants from Excel or sample data
- `POST /setup_tournament` - Initialize tournament, reset state, generate Round 1 (requires: PARTICIPANTS_LOADED)
- `POST /setup_round/<N>` - Generate round N if not already exists
- `POST /submit_table_results` - Submit results for a specific table (Phase 2: with validation, Phase 3.4: state-protected)
- `POST /submit_player_results` - Record scores, trigger next round generation
- `GET /get_tournament_state` - Full snapshot (standings, scores, current round, submission status)
- `GET /get_submission_status/<round_num>` - Get submission progress for a round (Phase 3.1)
- `GET /get_state_info` - Get current tournament state and valid next actions (Phase 3.4)
- `POST /generate_finals` - Create finals from top 4 teams (requires: SWISS_COMPLETE or TOP8_COMPLETE)

## Common Pitfalls

1. **Team vs Player Scores**: Both are tracked separately. `scores[team]` is aggregate of `player_scores[]` for all 4 team members. Must update both when submitting results.

2. **Round State Management**: Use `submitted_rounds` set to prevent double-submission. Always check `if round_num in self.submitted_rounds` before processing.

3. **Seating is Applied Post-Generation**: The constraint solver generates unordered pods. Seating logic runs afterward in `apply_intelligent_seating()`.

4. **Max Rounds is Dynamic**: Don't hardcode `if round_num == 5` for finals detection. Use `if round_num == self.max_rounds`.

5. **Excel Path is Hardcoded**: To change participant file location, search for `participants/participant_team.xlsx` in Flask routes in [tournament_dashboard.py](tournament_dashboard.py).

6. **Backup Feature is Disabled**: The `save_state()` and `load_state()` methods exist but should not be used. They cause state corruption.

## File Locations Reference

| Component | File | Key Functions/Classes |
|-----------|------|----------------------|
| Main application | [tournament_dashboard.py](tournament_dashboard.py) | TournamentManager (line 11), Flask routes (line 1400+) |
| Pairing algorithm | [unified_swiss_pairing.py](unified_swiss_pairing.py) | UnifiedSwissPairing (line 415), HybridConstraintSolver (line 46) |
| Frontend | [templates/dashboard_ultra_modern.html](templates/dashboard_ultra_modern.html) | CSS (lines 19-1466), JavaScript (lines 1467+) |
| Test suite | [test_tournament_comprehensive.py](test_tournament_comprehensive.py) | TournamentTester, comprehensive validation tests |
| Sample data generation | [tournament_dashboard.py:380](tournament_dashboard.py#L380) | create_sample_data() |
| Excel loading | [tournament_dashboard.py:261](tournament_dashboard.py#L261) | load_participants() |
| Intelligent seating | [tournament_dashboard.py:783-836](tournament_dashboard.py#L783-L836) | apply_intelligent_seating() |

## Known Limitations

- Single tournament per server instance
- No persistence (state lost on restart)
- Local-only by default (change to `host='0.0.0.0'` for network access)
- Manual score entry required (no external API integration)
- Backup/restore feature disabled due to bugs
