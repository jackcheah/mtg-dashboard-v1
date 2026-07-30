# MTG Tournament Dashboard

A production-ready web-based tournament management system for Magic: The Gathering (MTG) Commander (cEDH) tournaments. Supports both **team events** and **individual events** with Swiss-system rounds, automatic pairing, intelligent seating, and finals management.

## Features

- **Dual Event Modes**: Team events (4 players/team, 8-16 teams) and Individual events (16+ solo players)
- **Dual Scoring Systems**: Western (5/1/0) and Japanese (7% pool, 1000 starting points)
- **Swiss-System Pairing**: Round 1 random grouping, then score-based Swiss with repeat-avoidance optimization and anti-collusion snake pairing for rounds 3+
- **Individual Mode Extras**: Bye system, 3-player pods, player drop mid-tournament, Top Cut (top 10)
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
- **Team mode**: Top 4 teams (or Top 8 Cut + Top 4 for 16 teams)
- **Individual mode (≤16 players)**: Top 4 players advance directly to finals
- **Individual mode (>16 players)**: Top 10 advance to Top Cut, then Top 4 to finals

---

## Event Modes

### Team Mode

| Teams | Players | Swiss Rounds | Playoffs           | Total Rounds |
|-------|---------|--------------|--------------------|--------------|
| 8     | 32      | 3-5          | Finals (top 4)     | 4-6          |
| 12    | 48      | 3-5          | Finals (top 4)     | 4-6          |
| 16    | 64      | 3-5          | Top 8 Cut + Finals | 5-7          |

- Swiss rounds configurable (3, 4, or 5; default 4)
- 4 players per team, team standings
- Teammates never paired in same pod (hard constraint)
- **Round 1**: Random team grouping with player-level optimization
- **Round 2**: Traditional score-based Swiss (top 4 teams together, etc.)
- **Anti-collusion pairing** (rounds 3+): Snake interleave spreads top teams across pods to prevent intentional draws
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
- Total teams: 8, 12, or 16

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

## Testing

```bash
pip install -r requirements-dev.txt

# Unit tests (133 tests)
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
