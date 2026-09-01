# MTG Tournament Dashboard

A production-ready web-based tournament management system for Magic: The Gathering (MTG) Commander (cEDH) tournaments. Supports both **team events** and **individual events** with Swiss-system rounds, automatic pairing, intelligent seating, and finals management.

## Features

- **Dual Event Modes**: Team events (4 players/team, 8-40 teams) and Individual events (16+ solo players)
- **Dual Scoring Systems**: Western (5/1/0) and Japanese (7% pool, 1000 starting points)
- **Swiss-System Pairing**: Round 1 random grouping, then score-based Swiss with repeat-avoidance optimization and anti-collusion snake pairing for round 4+
- **Individual Mode Extras**: Bye system, 3-player pods, player drop mid-tournament, Top Cut (top 10)
- **TopDeck.gg Integration**: Export round pairings as CSV for TopDeck import — publish tournaments for public record and EDHTop16 consideration
- **Production-Ready**: Auto-backups every 5 minutes, crash recovery, thread-safe operations
- **Modern UI**: Responsive glassmorphism interface with step-by-step setup wizard
- **Projector View**: Dedicated read-only audience display with champion/MVP showcases

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python tournament_dashboard.py
# Dashboard: http://127.0.0.1:5001
# Projector: http://127.0.0.1:5001/projector
```

## Tournament Workflow
### Setup Flow
1. Click **"Load Participants"** to start the setup wizard
2. **Step 1**: Select Event Type (Team or Individual)
3. **Step 2**: Select Scoring Mode (Western or Japanese)
4. Participants load from `participants/participant_team.xlsx`. If not found, you'll be prompted to load sample data (shown with a DEMO MODE banner)
5. Click **"Setup Tournament"** to generate Round 1

### Playing Rounds
1. View pairings and seating assignments for the current round
2. Enter scores (W/D/L) for each table, click "Submit Table"
3. **(Individual mode)** After all tables submitted: optionally drop players
4. Click "Submit Round Results" to finalize and generate next round

### Finals
- **Team mode**: Top 4 teams (or Top 8 Cut + Top 4 for 16-40 teams)
- **Individual mode (≤16 players)**: Top 4 players advance directly to finals
- **Individual mode (>16 players)**: Top 10 advance to Top Cut, then Top 4 to finals

---

## Event Modes

### Team Mode

| Teams  | Players | Swiss Rounds | Playoffs           | Total Rounds |
|--------|---------|--------------|--------------------|--------------|
| 8      | 32      | 3-5          | Finals (top 4)     | 4-6          |
| 12     | 48      | 3-5          | Finals (top 4)     | 4-6          |
| 16-40  | 64-160  | 3-5          | Top 8 Cut + Finals | 5-7          |

- Swiss rounds configurable (3, 4, or 5; default 4 for 8-16 teams, 5 for 20-40 teams)
- 4 players per team, team standings
- Teammates never paired in same pod (hard constraint)
- **Round 1**: Random team grouping with player-level optimization
- **Rounds 2-3**: Traditional score-based Swiss (top 4 teams together, etc.)
- **Anti-collusion pairing** (round 4+): Snake interleave spreads top teams across pods to prevent intentional draws
- Tiebreakers: Team score → Best player → Average → Early wins

### Individual Mode

| Players | Swiss Rounds | Playoffs                   | Total Rounds |
|---------|--------------|----------------------------|--------------|
| 16      | 3-5          | Finals (top 4, 1 table)    | 4-6          |
| 17-64+  | 3-5          | Top Cut (top 10) + Finals  | 5-7          |

- Any number of players (minimum 16)
- Non-multiple-of-4 handling: 3-player pods and bye system
- Avoid repeat opponents (optimization, not hard constraint)
- **Player Drop**: TO can remove players between rounds (score frozen, excluded from future pairings)
- Tiebreakers: Score → Early wins

---

## Scoring Modes

### Western Mode (Default)
- **Win:** 5 points | **Draw:** 1 point | **Loss:** 0 points
- Players start at 0 points
- Team score = sum of all 4 players' scores

### Japanese Swiss Point Mode
- **Start:** Each player begins with 1000 points
- **Each round:** All players at table contribute 7% of current points to a pool
- **Win:** Winner takes the entire pool
- **Draw/Loss:** Players lose only their 7% contribution
- Points accumulate across rounds (never reset)
- See `JAPANESE-IMPLEMENTATION.md` for full details

---

## Individual Mode Features

### Bye System
When player count isn't divisible by 4:
- **Remainder 3**: Last 3 players form a 3-player pod (all play)
- **Remainder 1-2**: Bottom-ranked players get automatic byes
- Bye = Win (5pts Western, no change Japanese)

### 3-Player Pod Scoring
Valid outcomes for 3-player pods:
- 1 winner + 2 losers (5, 0, 0)
- 3 draws (1, 1, 1)
- 2 draws + 1 loser (1, 1, 0)

### Player Drop
- Available after all tables submit scores, before round finalization
- Dropped player's score is frozen (no further gains)
- Dropped players still appear in final standings
- Pairing engine rebuilds for next round with reduced player count

### Top Cut (>16 players)
- Top 10 players advance after Swiss rounds
- Top 2 seeds receive automatic byes
- Remaining 8 play in 2 tables of 4
- Top 4 advance to a single Finals table

---

## Configuration

### Custom Participants
Place an Excel file at `participants/participant_team.xlsx`:

**Team mode columns:** `Player ID`, `Player Name`, `Team Name`
- Teams must have exactly 4 players
- Total teams: 8 to 40 (any multiple of 4)

**Individual mode:** Same Excel format — the Team Name column is ignored. Each row is one player.

### PIN Protection (Optional)
```bash
TOURNAMENT_PIN=1234 python tournament_dashboard.py
```

### Backups & Reset
- Auto-saves every 5 minutes
- Manual: Click "Save Backup" in UI
- Restore: Restart server (auto-restores) or click "Restore Backup"
- **Reset Tournament**: Full reset to start over (requires typing "RESET" to confirm). Backup files are preserved and can still be restored

---

## Operator Features

- **Auto-restore on refresh**: If a tournament is in progress, the dashboard automatically restores the active round view on page load
- **Batch submit**: Submit all completed tables at once
- **Score editing**: Edit submitted scores before round finalization (with audit trail)
- **Revert submission**: Completely undo a table submission if needed
- **Unfinalize round**: Undo the most recently finalized round if a mistake is discovered (PIN-protected)
- **Undrop player**: Re-add a previously dropped player back into the tournament (PIN-protected)
- **TopDeck CSV Export**: One-click export of round pairings for TopDeck.gg import (with pre-export validation)

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **W** or **1** | Win (5 points) |
| **D** or **2** | Draw (1 point) |
| **L** or **3** | Loss (0 points) |
| **Tab** | Next player/button |
| **Ctrl+Enter** | Submit active table |
| **Esc** | Close modal |
| **?** | Show shortcuts help |

---

## Projector View

Access at `/projector` for audience-friendly display:
- Automatic view switching: Pairings → Standings → Champion
- High-contrast dark theme for projectors
- Champion display with MVP recognition

---

## TopDeck.gg Integration

The dashboard can export round pairings as CSV files for import into [TopDeck.gg](https://topdeck.gg), enabling public tournament records, decklist publication, and EDHTop16 submission.

### How It Works

After finalizing a round in the dashboard, click the **"TopDeck CSV"** button in the round controls bar. The system validates the round data, then downloads a CSV file you can upload directly to TopDeck.

### Step-by-Step Workflow

1. **Setup TopDeck event** (one-time): Create the event on TopDeck.gg with Game: `Magic: The Gathering`, Format: `EDH`, Team Size: `1`. Add your player roster. For team events, see "Team Mode Notes" below.

2. **Each round:**
   - Finalize the round in the dashboard (submit all tables → "Submit Round Results")
   - Click **"TopDeck CSV"** in the controls bar
   - Review any warnings in the modal, then confirm download
   - In TopDeck: open the round → **Round actions → Import pairings** → upload the CSV
   - Review TopDeck's reconciliation screen (check "New players" and "Not in file" lists)
   - Apply pairings, then enter results in TopDeck manually
   - End the TopDeck round when all tables are complete

3. **After the tournament:** Compare TopDeck standings against the dashboard. Submit the TopDeck event URL to EDHTop16 if desired.

### What Gets Exported

The CSV contains pairings only (not results):

```csv
table,player 1,player 2,player 3,player 4
1,Alice Tan,Ben Lim,Cheryl Ng,Daniel Lee
2,Emma Wong,Faris Rahman,Grace Koh,Hassan Ali
```

- One row per pod, four players per row (confirmed format)
- Sequential table numbers starting from 1
- Player names match what's in your roster
- UTF-8 encoded, CRLF line endings, standard CSV escaping
- For three-player pods (individual mode), `player 4` is exported as an empty field. **This has not been verified with TopDeck's live importer** — test in an unpublished TopDeck event before using in production

### Pre-Export Validation

Before downloading, the system checks for:

**Blocking errors** (must fix before export):
- Round not finalized
- Duplicate player names (TopDeck reconciles by name)
- Missing player names
- Wrong pod size in team mode (must be exactly 4)
- Teammates in the same pod
- Player assigned to multiple tables

**Warnings** (export allowed, review recommended):
- Dropped players absent from the round
- Bye players not included
- Three-player pods detected (unverified with TopDeck importer)

### Team Mode Notes

TopDeck does not support the dashboard's team format (4 teams contributing 1 player each to a pod). A team event must be mirrored on TopDeck as an **individual EDH event** (Team Size = 1). TopDeck will accurately record:

- Player roster and four-player pods
- Winner or draw of every pod
- Individual player records and decklists

TopDeck **will not** show: team scores, team standings, team-based advancement, or the winning team. The dashboard remains the authoritative source for team results.

**Recommended TopDeck event name:** `[Your Event] — Individual Results`

Include a description noting that advancement was determined by aggregate team score, not individual standings.

### API Endpoints

The export is also available via direct API calls:

| Endpoint | Description |
|----------|-------------|
| `GET /topdeck/validate/<round>` | Returns JSON: `{success, errors, warnings, summary}` |
| `GET /topdeck/export/<round>` | Downloads CSV file (validates first, returns 400 on error) |

### Scoring Configuration

Configure TopDeck scoring to match the dashboard:

**Western mode:** Standard scoring — Win: 5, Draw: 1, Loss: 0

**Japanese mode:** Not yet supported for TopDeck sync. Use manual entry in TopDeck until point-wager equivalence is confirmed.

### Full Specification

See `TopDeck_Integration_Specification.md` for the complete integration design, including: readback verification via the TopDeck API, webhook support, EDHTop16 submission workflow, and deferred features (results CSV, direct API sync).

---

## Testing

```bash
pip install -r requirements-dev.txt

# Unit tests (222 tests)
pytest tests/unit/ -v

# E2E (server must be running)
python tests/e2e/simulate_full_tournament.py --teams 8

# Concurrent access tests
python tests/e2e/test_concurrent.py
```

---

## Docker Deployment

```bash
docker-compose up -d --build
# Access at http://localhost:5001
```

---

## System Requirements
- Python 3.9+
- Modern web browser (Chrome, Firefox, Edge, Safari)
