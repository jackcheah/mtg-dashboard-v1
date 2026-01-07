# MTG Tournament Dashboard

A comprehensive web-based tournament management system for Magic: The Gathering (MTG) Commander (cEDH) tournaments. Supports Swiss-system rounds with automatic pairing, intelligent seating, and finals generation.

## Features

- **Swiss-System Tournament Management**: Supports 8, 12, or 16 teams (4 players per team)
- **Configurable Swiss Rounds**: Choose between 4 or 5 Swiss rounds  
- **Automatic Pairing**: Generates optimal pairings with zero repeat matchups
- **Intelligent Seating**: Score-based seating arrangements (higher-scored players at Seat 1)
- **Real-time Scoring**: Submit individual player scores and track team standings
- **Finals Generation**: Automatic advancement to finals based on standings
- **Modern UI**: Clean, responsive interface with real-time updates
- **Sample Data**: Built-in sample data for testing and demonstrations
- **Production-Ready Reliability**: Thread-safe operations, automatic backups, and crash recovery
- **Automatic Backup System**: Saves every 5 minutes + manual backup button for critical moments
- **Backup Rotation**: Keeps 4 backup files for recovery from corruption
- **Timer Persistence**: Tournament timer survives server restarts
- **Backup Health Monitoring**: Real-time visibility into backup status via /backup_health endpoint

- **Production-Ready Reliability**: Thread-safe operations, automatic backups, and crash recovery
- **Automatic Backup System**: Saves every 5 minutes + manual backup button for critical moments
- **Backup Rotation**: Keeps 4 backup files for recovery from corruption
- **Timer Persistence**: Tournament timer survives server restarts
- **Backup Health Monitoring**: Real-time visibility into backup status via /backup_health endpoint


## System Requirements

- Python 3.8 or higher
- Flask 2.0+
- Modern web browser (Chrome, Firefox, Edge, Safari)

## Installation

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd MTG-Tournament-Dashboard-AugmentCode
```

### 2. Install Dependencies

```bash
pip install flask openpyxl
```

Or using a virtual environment (recommended):

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install flask openpyxl

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install flask openpyxl
```

### 3. Run the Application

```bash
python tournament_dashboard.py
```

The dashboard will be available at: **http://127.0.0.1:5001**

## Quick Start Guide

### Setting Up a Tournament

1. **Start the Server**
   ```bash
   python tournament_dashboard.py
   ```

2. **Open the Dashboard**
   - Navigate to http://localhost:5001/ in your web browser

3. **Load Participants**
   - Click the "Load Participants" button
   - The system will automatically load sample data with 8 teams (32 players)
   - Or place your Excel file at `participants/participant_team.xlsx`

4. **Setup Tournament**
   - Click "Setup Tournament"
   - Round 1 pairings will be generated automatically

5. **Run Tournament Rounds**
   - For each table, click W (Win), D (Draw), or L (Loss) for players
   - Click "Submit Table Results" when all scores are entered
   - Click "Submit Round Results" to finalize the round
   - Next round will be generated automatically

6. **Finals**
   - After Swiss rounds complete, finals will be generated automatically
   - Top 4 teams advance to finals
   - Submit finals results to determine the champion

### Tournament Workflow
```
Load Participants → Setup Tournament → Swiss Rounds → Finals → Champion
```

Each round follows this cycle:
1. View pairings and seating assignments
2. Enter scores for each table
3. Submit table results
4. Submit round results (triggers next round generation)

## Tournament Structure

### Supported Team Counts

- **8 Teams** (32 players): 4 Swiss rounds → Finals (top 4)
- **12 Teams** (48 players): 4 Swiss rounds → Finals (top 4)
- **16 Teams** (64 players): 4 Swiss rounds → Top 8 Cut → Finals (top 4)

### Scoring System

**Individual Player Scores:**
- **Win**: 5 points
- **Draw**: 1 point
- **Loss**: 0 points

**Team Scores:**
- Sum of all 4 players' scores for each round
- Scores are tracked separately for each stage (Swiss, Top 8 Cut, Finals)
- Team advancement and rankings use stage-specific scoring

### Tournament Progression Logic

#### **16-Team Tournament:**

**Swiss Rounds (Rounds 1-4):**
- All 16 teams compete
- Scores accumulate across rounds
- Top 8 teams advance to Top 8 Cut

**Top 8 Cut (Round 5):**
- Top 8 teams compete in 8 tables (2 pods of 4 teams)
- **Swiss scores are saved and frozen**
- **Top 8 Cut scores tracked separately**
- Advancement to Finals determined by:
  - **PRIMARY:** Top 8 Cut round scores (Round 5 only)
  - **TIEBREAKER:** Swiss round scores (Rounds 1-4)
- Top 4 teams advance to Finals

**Finals (Round 6):**
- Top 4 teams compete in 4 tables (1 pod)
- **Finals scores tracked separately**
- Champion determined by:
  - **PRIMARY:** Finals round scores (Round 6 only)
  - **TIEBREAKER:** Swiss + Top 8 Cut combined scores
- Winner receives championship trophy

#### **8-Team & 12-Team Tournaments:**

**Swiss Rounds (Rounds 1-4):**
- All teams compete
- Scores accumulate across rounds
- Top 4 teams advance to Finals

**Finals (Round 5):**
- Top 4 teams compete in 4 tables (1 pod)
- **Swiss scores saved and frozen**
- **Finals scores tracked separately**
- Champion determined by:
  - **PRIMARY:** Finals round scores (Round 5 only)
  - **TIEBREAKER:** Swiss round scores (Rounds 1-4)

### Key Principles

1. **Current Round Performance Matters Most**: Advancement and winning are primarily determined by performance in the current playoff round
2. **Previous Rounds as Tiebreakers**: Earlier round scores are only used to break ties
3. **Separate Score Tracking**: Each stage (Swiss, Top 8 Cut, Finals) tracks scores independently
4. **Fair Competition**: Teams cannot coast on early performance - they must perform in each playoff stage

### Pairing Algorithm

**Constraints:**
- **Team Separation**: Teammates NEVER paired together (hard constraint)
- **Zero Repeat Matchups**: Guaranteed no teams face each other twice

**Round Generation:**
- **Round 1**: Random pairing with random seating
- **Rounds 2+**: Swiss pairing based on team standings
- **Intelligent Seating**: Players seated by individual score (highest at Seat 1)
- **Incremental**: Each round generated after previous round submission

## Key Features & Shortcuts

### UX Improvements
- **Auto-Fill Losers**: Selecting "Win" (5 pts) for a player automatically marks teammates as "Loss" (0 pts) to save clicks.
- **Batch Submit**: Submit all completed tables in a round with one click.
- **Compact Mode**: Toggle for a denser view (great for 16-table tournaments). Persists across reloads.
- **Smart Visuals**: Pulsing timer near round end; dimmed cards for submitted tables.

### Live Bracket Display (Top 8 Cut & Finals)

**Real-Time Score Updates:**
- Bracket displays **current round scores only** (not accumulated totals)
- Updates automatically as tables are submitted
- Shows team rankings with Swiss scores as tiebreaker

**Accurate Matchup Display:**
- Top 8 Cut: Shows 2 pods of 4 teams matching actual table assignments
- Finals: Shows single pod with all 4 teams
- Pod groupings reflect actual table pairings (not just theoretical matchups)

**Visual Indicators:**
- Teams sorted by current round performance
- Info icon explains pairing logic
- Score progression visible in real-time

### Projector View

**Read-Only Display for Audience:**
- Access at `/projector` for a full-screen, audience-friendly display
- Large timer with visual warnings (color changes at 90%, blinking when over)
- Automatic view switching: Pairings → Standings → Champion
- High-contrast dark theme optimized for projectors

### Keyboard Shortcuts
Press `?` (Shift+/) at any time to see this list in the app.

| Key | Action |
|-----|--------|
| **W** or **1** | Win (5 points) |
| **D** or **2** | Draw (1 point) |
| **L** or **3** | Loss (0 points) |
| **Tab** | Next player/button |
| **Shift+Tab** | Previous player/button |
| **Ctrl+Enter** | Submit active table |
| **Esc** | Close modal |

## File Structure

```
mtg-dashboard-v1/
├── tournament_dashboard.py          # Main Flask application (~3870 lines)
├── unified_swiss_pairing.py         # Swiss pairing algorithm (~2130 lines)
├── templates/
│   ├── dashboard_ultra_modern.html  # Frontend UI template (~4640 lines)
│   └── projector_view.html          # Read-only projector display (~670 lines)
├── participants/                    # Excel participant files
│   └── participant_team.xlsx        # Default Excel file path
├── tests/
│   └── e2e/                         # End-to-End test suite
│       ├── simulate_tournament_flow.py  # Basic E2E simulation
│       ├── simulate_full_tournament.py  # Comprehensive E2E with tracking
│       └── generate_16_teams.py         # Test data generator
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker container configuration
├── docker-compose.yml               # Docker Compose setup
├── README.md                        # User documentation (this file)
├── CLAUDE.md                        # Developer/AI assistant guide
└── TOURNAMENT_SCORING_SYSTEM.md     # Detailed scoring documentation
```

## Using Custom Participant Data

### Option 1: Use the Default Path
Create a directory and Excel file at: `participants/participant_team.xlsx`

```bash
mkdir participants
# Place your Excel file in this directory as participant_team.xlsx
```

### Option 2: Use Sample Data (Recommended for Testing)
If no Excel file is found, the system automatically loads sample data with 8 teams (32 players). No setup required!

### Excel File Format

**Required columns:**
- Player ID (integer)
- Player Name (string)
- Team Name (string)

**Important:**
- Teams must have exactly 4 players
- Total teams must be 8, 12, or 16
- Player IDs must be unique

**Note:** To use a different file path, edit line 1358 in `tournament_dashboard.py`:
```python
excel_path = 'your/custom/path/to/file.xlsx'
```

## Testing (E2E)

A comprehensive **End-to-End test suite** is available in `tests/e2e/`:

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Run E2E simulation (server must be running)
cd tests/e2e
python simulate_tournament_flow.py          # Basic simulation
python simulate_full_tournament.py          # Full simulation with tracking
```

The E2E tests validate:
- **Swiss Pairing Rules**: No repeat matchups, teammate separation
- **Phase Transitions**: Swiss → Top 8 Cut → Finals
- **Champion Declaration**: Tournament completes successfully

See `tests/e2e/README.md` for detailed documentation.

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or use the convenience scripts
./build-and-run.sh    # Mac/Linux
.\build-and-run.bat   # Windows
```

## Troubleshooting

### Round 2 Not Generating

**Solution:**
1. Refresh browser (F5)
2. Select "Swiss Round 2" from dropdown
3. Ensure all tables submitted before "Submit Round Results"

### Player Scores Show 0

**Solution:**
1. Refresh page (F5) to reload scores
2. Backend tracks correctly (check team standings)

### "Round already submitted" Error

**Solution:**
1. Click "Load Participants"
2. Click "Setup Tournament"
3. Happens if page left open between server restarts

## Production Features (New!)

### Automatic Backup & Recovery System

The system now includes enterprise-grade backup and recovery features for reliable 12+ hour operation:

**Automatic Backups:**
- Saves tournament state every 5 minutes automatically
- Backs up after every critical operation (load, setup, score submission)
- Keeps 4 backup files: current + 3 historical versions
- Backup rotation protects against file corruption

**Manual Backup:**
- "Save Backup Now" button in Setup Tournament Controls
- Use before critical transitions (Round 4, Top 8 Cut, Finals)
- Instant feedback with toast notifications

**Crash Recovery:**
- Server automatically restores state from backup on startup
- Timer continues from where it left off
- All scores, pairings, and tournament state preserved

**Backup Health Monitoring:**
- Visit `http://127.0.0.1:5001/backup_health` to check backup status
- Shows last success/failure timestamps
- Tracks consecutive backup failures
- Displays backup file size and location

**Thread Safety:**
- All operations protected with locks for concurrent access
- Safe to have multiple browser windows open
- No data corruption from simultaneous score submissions

### How to Use:

1. **Before Event:** Test the "Save Backup Now" button
2. **During Event:** System auto-saves every 5 minutes (watch console for "[AUTO-BACKUP]" messages)
3. **Manual Backups:** Click "Save Backup Now" before Round 4, Top 8 Cut, and Finals
4. **Monitor Health:** Check console logs for backup success/failure messages
5. **If Server Crashes:** Just restart - it auto-restores from backup!

### Backup Files Location:
- `tournament_state.json.bak` (current backup)
- `tournament_state.json.bak.1` (1 save ago)
- `tournament_state.json.bak.2` (2 saves ago)  
- `tournament_state.json.bak.3` (3 saves ago)

---

## Known Limitations

1. Single tournament at a time
2. ~~No persistence~~ **Now has automatic backups!** State persists across restarts
3. Local-only by default
4. Manual scoring required

## For Local PC Use

**Running this locally on your PC?** Perfect!
- ✅ **100% Production Ready** - Enhanced with automatic backups and crash recovery
- ✅ **Perfectly Secure** - Not exposed to internet = no security concerns
- ✅ **12+ Hour Stable** - Automatic backups every 5 minutes + timer persistence
- ✅ **Crash Recovery** - Server restart? No problem! Auto-restores from backup
- ✅ **Manual Control** - "Save Backup Now" button for peace of mind
- ✅ Keep Python and browser running during tournament (but restarts are safe now!)

## Credits

Developed for Knights of Round Table - cEDH Team Championship tournaments.
