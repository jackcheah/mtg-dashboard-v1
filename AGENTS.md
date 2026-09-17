# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

MTG Tournament Dashboard is a production-ready web-based tournament management system for **Magic: The Gathering cEDH tournaments**. It supports both **team events** (4 players per team) and **individual events** (solo players). It implements Swiss-system pairing with automatic round generation, intelligent seating, and finals management.

**Tech Stack:** Python 3.9+ | Flask 3.0+ | Vanilla JavaScript | In-memory state management (with JSON persistence)
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
pytest tests/unit/ -v                                        # 222 unit tests
python tests/e2e/simulate_full_tournament.py --teams 8       # E2E (server must be running)
python tests/e2e/test_concurrent.py                          # Concurrent access tests
```

---

## Event Modes

The system supports two event modes, selected before loading participants:

### Team Mode (default)
- 4 players per team, 8-40 teams (any multiple of 4)
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

Swiss rounds are configurable: 3, 4, or 5 via `setup_tournament(swiss_rounds=N)` or `/set_swiss_rounds`. Defaults are aligned with TopDeck.gg recommended structure (each team = 1 "player" for TopDeck's table).

| Teams  | Players | Swiss Rounds (default) | Playoffs           | Total Rounds |
|--------|---------|-----------------------|--------------------|--------------|
| 8-16   | 32-64   | 3                     | Finals (top 4)     | 4            |
| 20-32  | 80-128  | 4                     | Finals (top 4)     | 5            |
| 36-40  | 144-160 | 5                     | Top 8 Cut + Finals | 7            |

### Individual Mode

| Players | Swiss Rounds | Playoffs                          | Total Rounds |
|---------|--------------|-----------------------------------|--------------|
| ≤16     | 3-5          | Finals (top 4)                    | 4-6          |
| 17+     | 3-5          | Top Cut (top 10) + Finals (top 4) | 5-7          |

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
| **TopDeck Exporter** | `topdeck_exporter.py` | Pure-logic module for TopDeck.gg CSV pairings export. Zero dependencies on Flask or TournamentManager. |
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
- **`UnifiedSwissPairing._generate_round_individual_mode()`** (in `unified_swiss_pairing.py`): Score-sorted Swiss pairing for individuals with swap optimization.
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
| `/load_data` | GET, POST | Load participants from Excel. Returns `offer_sample: true` if file missing (sample data requires explicit opt-in via `use_sample_data: true`) |
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
| `/set_swiss_rounds` | POST | Set Swiss round count (3, 4, or 5) |
| `/unfinalize_round` | POST | Undo most recently finalized round (PIN-protected) |
| `/undrop_player` | POST | Re-add a dropped player (PIN-protected) |
| `/get_tables/<round>` | GET | Table assignments for a specific round |
| `/get_teams` | GET | All teams and players |
| `/get_scores` | GET | Current team scores |
| `/get_player_scores` | GET | Individual player scores |
| `/standings` | GET | Current sorted standings |
| `/find_player/<player_id>` | GET | Find which table a player is at |
| `/search_player` | GET | Search player by name (query param `q`) |
| `/validate_integrity` | GET | Tournament data integrity check |
| `/validate_round/<round>` | GET | Validate Swiss pairings for a round |
| `/bracket_groups/<round>` | GET | Bracket display groupings |
| `/bracket_standings/<round>` | GET | Bracket standings for visualization |
| `/list_backups` | GET | List available backup files |
| `/backup_health` | GET | Backup health status |
| `/tournament_statistics` | GET | Detailed stats and validation info |
| `/get_score_history/<round>/<table>` | GET | Score edit audit trail |
| `/projector` | GET | Projector audience view |
| `/` | GET | Main dashboard page |
| `/configure_swiss_rounds` | POST | Configure Swiss round count (alias for /set_swiss_rounds) |
| `/setup_round/<round>` | GET | Get setup info for a specific round |
| `/validate_full_swiss` | GET | Validate all Swiss rounds |
| `/get_all_swiss_rounds` | GET | Get data for all Swiss rounds |
| `/get_semifinals` | GET | Get semifinals/Top Cut data |
| `/get_final_standings` | GET | Get final standings data |
| `/get_finals` | GET | Get finals round data |
| `/preview_finalize/<round>` | GET | Preview what finalization will produce |
| `/topdeck/validate/<round>` | GET | Pre-export validation for TopDeck CSV (errors, warnings, summary) |
| `/topdeck/export/<round>` | GET | Download TopDeck-compatible pairings CSV for a finalized round |

---

## TopDeck.gg Integration

### Overview

The dashboard can export round pairings as CSV files compatible with TopDeck.gg's **Round actions → Import pairings** feature. This allows operators to publish cEDH tournaments on TopDeck for public record-keeping, decklist publication, and EDHTop16 consideration.

**V1 scope:** Pairings CSV export only. Results must be entered manually in TopDeck after import. Results-in-CSV export is deferred until TopDeck's exact result column schema is confirmed.

**Specification:** Full integration design is documented in `TopDeck_Integration_Specification.md`.

### Architecture

The exporter is a **separate pure-logic module** (`topdeck_exporter.py`) with zero dependencies on Flask or `TournamentManager`. It receives plain Python dicts/lists and returns CSV bytes or validation results. Two thin Flask endpoint wrappers in `tournament_dashboard.py` extract data from the `tournament` singleton and pass it to the exporter. The UI triggers these endpoints via the "TopDeck CSV" button in the active round controls bar.

```
Dashboard UI (button click)
    → JS exportTopdeck() calls GET /topdeck/validate/<round>
    → Shows errors/warnings via modal
    → On success, triggers GET /topdeck/export/<round>
    → Browser downloads CSV file

Flask endpoints (tournament_dashboard.py)
    → Extract tables, finalized_rounds, event_mode, teams, etc. from tournament singleton
    → Pass plain data to topdeck_exporter functions
    → Return JSON (validate) or CSV Response (export)

topdeck_exporter.py (pure functions, no Flask dependency)
    → validate_round_for_topdeck() → {errors, warnings, summary}
    → build_pairings_csv() → UTF-8 bytes
    → extract_table_number() → int
    → generate_export_filename() → string
```

### TopDeck CSV Format

The exported CSV follows TopDeck's documented pairings import schema:

```csv
table,player 1,player 2,player 3,player 4
1,Alice Tan,Ben Lim,Cheryl Ng,Daniel Lee
2,Emma Wong,Faris Rahman,Grace Koh,Hassan Ali
```

Rules:
- First column is `table` (sequential positive integers starting from 1).
- Player columns are `player 1` through `player 4` (confirmed by TopDeck documentation).
- Each row is one multiplayer pod.
- Team-mode pods always have exactly 4 players.
- Individual-mode 3-player pods leave `player 4` empty. **Unverified with TopDeck's live importer** — test in an unpublished event before production use.
- Player names are stripped of leading/trailing whitespace.
- Names with commas, apostrophes, or unicode are properly CSV-escaped.
- Output is UTF-8 encoded (our choice; not explicitly documented as a TopDeck requirement) and deterministic for unchanged input.
- Line endings are CRLF (safe standard; not explicitly required by TopDeck).
- Filename: `topdeck_round_03_pairings.csv` (our convention; not enforced by TopDeck).

### Exporter Module (`topdeck_exporter.py`)

Four pure functions:

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `extract_table_number(table_name)` | `str` (e.g., `"Table 1"`, `"Semifinals Table 3"`, `"Finals Table"`) | `int` | Extracts trailing integer from table name. Returns `1` when no number found. |
| `validate_round_for_topdeck(tables, round_num, finalized_rounds, event_mode, teams, dropped_players, bye_players)` | Plain dicts/lists from tournament state | `dict` with `errors`, `warnings`, `summary` | Pre-export validation. All params are plain Python types, not TournamentManager. |
| `build_pairings_csv(tables, event_mode)` | Validated table data | `bytes` (UTF-8 CSV) | Generates the CSV. Assumes caller has validated. |
| `generate_export_filename(round_num, event_name)` | `int`, optional `str` | `str` | Returns filename like `topdeck_round_03_pairings.csv`. |

### Validation

The validate endpoint (`GET /topdeck/validate/<round>`) runs all checks before allowing export.

**Blocking errors** (export is prevented):
- Round does not exist or has no tables
- Round has not been finalized
- Duplicate table numbers
- Duplicate player ID across tables (player assigned to multiple tables)
- Duplicate exported player name (TopDeck reconciles by name)
- Missing or empty player name
- Team-mode pod with fewer or more than 4 players
- Teammates seated together in team mode

**Warnings** (export proceeds, operator should review):
- Dropped players absent from the round
- Bye players not included
- Three-player pods detected (unverified with TopDeck's CSV importer — test in an unpublished event first) in the export

**Validation summary** (always returned):
```json
{
  "round": 3,
  "tables": 8,
  "players_exported": 32,
  "players_omitted": 0,
  "duplicate_players": 0,
  "team_conflicts": 0,
  "result_data_included": false,
  "status": "Ready for TopDeck import"
}
```

### Flask Endpoints

**`GET /topdeck/validate/<int:round_num>`**
- State guard: `TOURNAMENT_SETUP`, `SWISS_IN_PROGRESS`, `TOP8_IN_PROGRESS`, `FINALS_IN_PROGRESS`, `FINALS_COMPLETE`
- Returns: `{success, errors, warnings, summary}`
- No PIN required (read-only)

**`GET /topdeck/export/<int:round_num>`**
- Same state guard as validate
- Runs validation first — returns 400 with errors if blocked
- On success: returns CSV with `Content-Disposition: attachment; filename=topdeck_round_NN_pairings.csv`
- No PIN required (read-only)

### UI Button

The "TopDeck CSV" button is in the active round controls bar (`#active-round-controls`), between "Save Backup" and "Reset". It uses `btn-secondary` styling (white/border) to visually distinguish it from primary tournament actions.

**JS function `exportTopdeck()`** (in `static/js/dashboard.js`):
1. Gets the selected round number from `#round-select`
2. Calls `GET /topdeck/validate/<round>` to check readiness
3. If errors: shows a modal listing all blocking errors
4. If warnings only: shows a confirm dialog with "Download" / "Cancel"
5. If clean: triggers CSV download via `window.location.href` and shows a success toast with summary

### Operator Workflow (Per Round)

1. Generate and verify the round in the dashboard.
2. Submit all table scores and finalize the round.
3. Click **"TopDeck CSV"** in the controls bar.
4. Review any warnings in the modal (e.g., dropped players).
5. CSV downloads automatically.
6. In TopDeck: open the corresponding round → **Round actions → Import pairings** → upload CSV.
7. Review TopDeck's reconciliation screen (new players, missing players).
8. Apply pairings, then enter or confirm results in TopDeck manually.
9. Repeat for each subsequent round.

### Team Mode Considerations

TopDeck cannot represent aggregate team standings. A team event MUST be mirrored as an individual EDH event (Team Size=1) on TopDeck. The TopDeck event accurately records:
- The actual player roster and four-player pods
- The winner or draw of every pod
- Each player's individual record and decklists

TopDeck CANNOT represent: team scores, team rank, team-based advancement, or a team champion. The dashboard remains authoritative for those values. See `TopDeck_Integration_Specification.md` Section 3.2 for full rationale.

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

### Unit Tests (222 tests)
```bash
pytest tests/unit/ -v
```
Covers: tiebreaker logic, final standings, MVP, state machine, backup/restore integrity, score validation, reset confirmation, individual mode, anti-collusion pairing, full tournament flow simulation (8-40 teams), pairing engine simulation, TopDeck CSV export validation and generation.

### E2E Tests
```bash
python tests/e2e/simulate_full_tournament.py --teams [8|12|16|20|24|28|32|36|40]
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
├── tournament_dashboard.py          # Main Flask app + TournamentManager + TopDeck endpoints
├── unified_swiss_pairing.py         # Pairing algorithm (team + individual modes)
├── topdeck_exporter.py              # TopDeck.gg pairings CSV export (pure logic, no Flask deps)
├── static/
│   ├── css/dashboard.css            # Dashboard styles
│   └── js/dashboard.js              # Dashboard logic (event mode, scoring, drops, TopDeck export)
├── templates/
│   ├── dashboard_ultra_modern.html  # Dashboard HTML (event/scoring mode modals, TopDeck button)
│   └── projector_view.html          # Projector display
├── tests/
│   ├── unit/
│   │   ├── test_tournament_manager.py  # Core tournament logic tests
│   │   ├── test_individual_mode.py     # Individual mode tests
│   │   ├── test_new_endpoints.py       # Endpoint tests
│   │   ├── test_pairing.py            # Pairing algorithm tests
│   │   ├── test_scoring.py            # Scoring logic tests
│   │   ├── test_state_machine.py      # State machine tests
│   │   ├── test_validation.py         # Validation tests
│   │   └── test_topdeck_exporter.py   # TopDeck CSV export tests (44 tests)
│   └── e2e/
│       ├── simulate_full_tournament.py # Playwright E2E
│       ├── simulate_tournament_flow.py # Flow simulation
│       ├── test_concurrent.py          # Concurrent access tests
│       ├── generate_teams.py           # Test data generator (8/12 teams)
│       └── generate_16_teams.py        # Test data generator (16 teams)
├── participants/
│   └── participant_team.xlsx        # Participant data
├── TopDeck_Integration_Specification.md  # Full TopDeck integration design spec
├── Dockerfile                       # Docker container config
├── docker-compose.yml               # Docker compose deployment
├── JAPANESE-IMPLEMENTATION.md       # Japanese scoring mode documentation
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Dev/test dependencies
├── AGENTS.md                        # This file
└── README.md                        # User documentation
```

---

## Swiss Pairing Implementation

### Team Mode (`unified_swiss_pairing.py`)

**Round 1 (Random Grouping):**

1. **Group**: Teams are shuffled randomly into groups of 4.
2. **Optimize** (Layer 3): Permutation search to minimize player-level repeats. Multiple perfect solutions collected and one chosen randomly for enhanced variety.
3. **Guarantees**: No teammates in same pod.

**Rounds 2-3 (Traditional Swiss):**

1. **Group**: Sort teams by score into brackets of 4 (top 4 → Group 1, next 4 → Group 2, etc.).
2. **Swap** (Layer 2): If repeats/conflicts exist, swap lowest team with nearest neighbor in adjacent brackets.
3. **Optimize** (Layer 3): Permutation search to minimize player-level repeats.
4. **Guarantees**: No teammates in same pod. Zero repeat matchups for 16+ teams / 3 Swiss rounds.

**Round 4+ (Anti-Collusion Snake Pairing):**

To prevent top teams from colluding via intentional draws, round 4+ uses snake/interleave grouping that spreads top teams across different pods. This only activates for tournaments with 4+ Swiss rounds (20+ teams by default):

1. **Snake Group**: Teams sorted by score, then assigned in snake order — each pod gets one team from each quartile.
2. **Swap** (Layer 2): Same repeat-avoidance swaps still apply on top.
3. **Optimize** (Layer 3): Same player-level optimization still applies.

Snake distribution (16 teams, 4 groups):

- Group 1: seeds 1, 8, 9, 16
- Group 2: seeds 2, 7, 10, 15
- Group 3: seeds 3, 6, 11, 14
- Group 4: seeds 4, 5, 12, 13

Configuration (in `TournamentManager`):

- `anti_collusion_enabled`: Default `True` (team mode only, ignored for individual)
- `anti_collusion_start_round`: Default `4` (rounds before this use traditional Swiss)

### Individual Mode (`_generate_round_individual_mode()`)

1. **Sort**: All players sorted by score (descending).
2. **Chunk**: Group into pods of 4 (bottom remainder gets byes or forms 3-player pod).
3. **Optimize**: Swap players between adjacent pods to minimize repeat opponents.
4. **Engine rebuild**: After player drops, engine is recreated with reduced player list.
