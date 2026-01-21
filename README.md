# MTG Tournament Dashboard

A comprehensive web-based tournament management system for Magic: The Gathering (MTG) Commander (cEDH) tournaments. Supports Swiss-system rounds with automatic pairing, intelligent seating, and finals generation.

## Features

- **Swiss-System Management**: Supports 8, 12, or 16 teams (4 players per team).
- **Automated Workflow**: Automatic pairing (no repeats), intelligent seating (by score), and round generation.
- **Robust Scoring**: Track individual and team scores with a comprehensive tiebreaker system.
- **Production-Ready**: Automatic backups every 5 minutes, crash recovery, and thread-safe operations.
- **Modern UI**: Responsive "Ultra Modern" glassmorphism interface with dark mode.
- **Projector View**: Dedicated read-only display for audiences with champion and MVP showcases.

## System Requirements
- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Edge, Safari)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd MTG-Tournament-Dashboard
```

### 2. Install Dependencies
```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install flask openpyxl

# Windows
python -m venv venv
venv\Scripts\activate
pip install flask openpyxl
```

## Quick Start

### 1. Run the Application
```bash
# activate your venv first, then:
python tournament_dashboard.py
```
Access the dashboard at: **http://127.0.0.1:5001**

### 2. Tournament Workflow
1.  **Load Participants**: Click "Load Participants" (loads `participants/participant_team.xlsx` or sample data).
2.  **Setup**: Click "Setup Tournament" to generate Round 1.
3.  **Swiss Rounds**: 
    - Enter results (W/D/L) for each table. 
    - Click "Submit Table" -> "Submit Round". 
    - Repeat for 4 rounds.
4.  **Finals**: The system automatically generates Top 8 (for 16 teams) or Finals (for 8/12 teams).

### Key Shortcuts
- **W / 1**: Win
- **D / 2**: Draw
- **L / 3**: Loss
- **Tab**: Next input
- **Ctrl+Enter**: Submit Table
- **?**: View all shortcuts

## Configuration

### Custom Participants
To use your own roster, create an Excel file at `participants/participant_team.xlsx` with columns: `Player ID`, `Player Name`, `Team Name`.
- Teams must have exactly 4 players.
- Total teams must be 8, 12, or 16.

### Backups
The system automatically backs up state every 5 minutes.
- **Manual Backup**: Click "Save Backup" in the UI before critical rounds.
- **Restoration**: Just restart the server (`python tournament_dashboard.py`) to auto-restore the last valid state.

## Tournament Rules & Structure

### Structure
- **8 Teams**: 4 Swiss Rounds → Finals (Top 4)
- **12 Teams**: 4 Swiss Rounds → Finals (Top 4)
- **16 Teams**: 4 Swiss Rounds → Top 8 Cut → Finals (Top 4)

<<<<<<< HEAD
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

### Scoring & Advancement System

The system uses a stage-based scoring approach where performance in the current stage acts as the primary advancement criteria, while previous stages serve as tiebreakers.

#### 1. Core Principles
1.  **Stage-Specific Scoring**: Scores are tracked separately for Swiss, Top 8 Cut, and Finals.
2.  **Performance-Based Advancement**: Teams advance based on performance in the *current* stage.
3.  **Multi-Level Tiebreakers**: Comprehensive tiebreaker system ensures fair advancement.
4.  **No Score Carrying**: Teams cannot "coast" on early performance.

#### 2. Scoring Modes

The tournament supports two scoring modes, selected after loading participants:

**Western Mode (Default)**
-   **Win:** 5 points | **Draw:** 1 point | **Loss:** 0 points
-   Players start with 0 points
-   **Team Score:** Sum of all 4 players' scores for the round.

**Japanese Swiss Point Mode**
-   **Start:** Each player begins with 1000 points
-   **Each round:** All players contribute 7% of current points to pool
-   **Win:** Winner takes the entire pool (~280 pts in round 1)
-   **Draw/Loss:** Players lose their 7% contribution
-   Points accumulate across rounds (never reset)
-   See `JAPANESE-IMPLEMENTATION.md` for full details

#### 3. Tournament Stages (16-Team Format)

**Stage 1: Swiss Rounds (Rounds 1-4)**
-   All 16 teams compete.
-   Scores accumulate across all 4 rounds.
-   **Top 8** teams based on total Swiss scores advance to the Top 8 Cut.
-   **Tiebreaker Hierarchy:**
    1.  Total Team Score (primary)
    2.  Best Individual Player Score
    3.  Average Player Score
    4.  Early Wins Score (Round 1 > Round 2 > Round 3 > Round 4)

**Stage 2: Top 8 Cut (Round 5)**
-   8 Teams compete in 2 pods of 4.
-   **Scoring:** Only points earned in Round 5 count towards advancement.
-   **Advancement Criteria:**
    1.  **Primary:** Points earned in Top 8 Cut (Round 5).
    2.  **Tiebreakers:** Swiss Score → Best Player → Average → Early Wins
-   **Top 4** teams advance to Finals.

**Stage 3: Finals (Round 6)**
-   4 Teams compete in a single pod.
-   **Scoring:** Only points earned in Round 6 count for the title.
-   **Champion Determination:**
    1.  **Primary:** Points earned in Finals (Round 6).
    2.  **Tiebreaker:** Combined Swiss + Top 8 Cut Points (Rounds 1-5).
-   **MVP Award:** Highest individual scorer among Top 4 teams.

*(Note: For 8/12-team formats, the Top 8 Cut is skipped, and top 4 from Swiss advance directly to Finals.)*

### Pairing & Seating Algorithm

**1. Traditional Swiss Pairing**
-   **Goal:** Winners play Winners. Teams are grouped by score brackets.
-   **Constraint - Zero Repeats:** Teams will never face the same opponent twice.
-   **Constraint - Teammate Avoidance:** Teammates will never be paired at the same table.
-   **Optimization:** If a repeat is unavoidable in a bracket, the system swaps the lowest-ranked team with a neighbor, minimizing score disruption.

**2. Intelligent Seating**
-   Players are seated at the table based on their individual performance.
-   **Seat 1:** Highest individual scorer.
-   **Seat 4:** Lowest individual scorer.
-   This balances the "Pod A/B/C/D" strength across the tournament.

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
- **Champion Display:** Horizontal split layout (champion on left, finalists + MVP on right)
- **Detailed Scores:** Shows Final, Top Cut, and Swiss scores with visual hierarchy
- **MVP Recognition:** Displays highest individual scorer from Top 4 teams

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
├── tournament_dashboard.py          # Main Flask application (~4000 lines)
├── unified_swiss_pairing.py         # Swiss pairing algorithm (~2370 lines)
├── templates/
│   ├── dashboard_ultra_modern.html  # Frontend UI template (~5530 lines)
│   └── projector_view.html          # Read-only projector display (~700 lines)
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
├── TOURNAMENT_SCORING_SYSTEM.md     # Detailed scoring documentation
├── PHASE5-IMPLEMENTATION-SUMMARY.md # Phase 5 implementation details (projector/tiebreakers)
├── PHASE2-IMPLEMENTATION-SUMMARY.md # Phase 2 implementation details
└── PHASE1-IMPLEMENTATION-SUMMARY.md # Phase 1 implementation details
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

**Note:** To use a different file path, edit line 1819 in `tournament_dashboard.py`:
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
=======
### Scoring
- **Win**: 5 pts | **Draw**: 1 pt | **Loss**: 0 pts
- **Advancement**: Based on current stage performance.
- **Tiebreakers**: Total Score → Best Player → Average Player → Early Wins.
>>>>>>> 9b5323584877a48f640347c2bfae5f205aff42b0

## Troubleshooting

- **Round Not Generating**: Ensure all tables in the current round are submitted. Refresh the page.
- **App Not Loading**: Check if port 5001 is in use or the terminal window is closed.
- **Data Mismatch**: Restart the server to reload ground-truth state from the backup file.

## Credits
Developed for **Knights of Round Table** - cEDH Team Championship tournaments.
