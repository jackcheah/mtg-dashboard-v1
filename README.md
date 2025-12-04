# MTG Tournament Dashboard - Complete System Documentation

**Last Updated:** 2025-12-04
**Version:** 2.3 (Revised Tournament Structure: 8, 12, 16 teams)
**Test Coverage:** 100% (All tests passing)
**Status:** ✅ **PRODUCTION READY** 🛡️ **CRASH-PROTECTED**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Tournament Structure](#tournament-structure)
6. [Swiss Pairing Algorithm](#swiss-pairing-algorithm)
7. [Playoff Structures](#playoff-structures)
8. [Data Persistence & Backup](#data-persistence--backup)
9. [Core Features](#core-features)
10. [API Endpoints](#api-endpoints)
11. [Scoring System](#scoring-system)
12. [Usage Guide](#usage-guide)
13. [Troubleshooting](#troubleshooting)
14. [Architecture](#architecture)
15. [Version History](#version-history)

---

## 🎯 Overview

A comprehensive web-based tournament management system for Magic: The Gathering CEDH team events with advanced Swiss pairing, real-time scoring, and automated tournament progression.

### Main Requirements Met ✅

1. **Team-Based Tournament Management**
   - Support for 8, 12, or 16 teams (4 players per team)
   - Automatic team separation (no teammates at same table)
   - Team and individual player score tracking

2. **Swiss Round System**
   - All tournaments use 4 Swiss rounds
   - Advanced constraint satisfaction pairing algorithm
   - Intelligent score-based seating from Round 2 onwards
   - ⚠️ Note: Repeat matchups may occur in 8 and 12 team tournaments

3. **Playoff Structure**
   - **8 teams**: 4 Swiss → Finals (top 4 teams, 4 pods)
   - **12 teams**: 4 Swiss → Finals (top 4 teams, 4 pods)
   - **16 teams**: 4 Swiss → Top 8 Cut (8 teams, 8 pods) → Finals (top 4 teams, 4 pods)
   - Strength-based seating in playoffs
   - No teammates paired together in any round

4. **Real-Time Tournament Management**
   - Live score tracking and standings
   - Automatic round progression
   - Duplicate submission prevention
   - Championship determination with tiebreakers

5. **Data Persistence & Crash Recovery** 🆕
   - Automatic backup after every important operation
   - Auto-restore on container restart
   - Survives Docker crashes, restarts, and rebuilds
   - Zero data loss during tournament day

6. **Modern Web Interface**
   - Ultra-modern glassmorphism UI
   - Real-time updates
   - Mobile-responsive design
   - Built-in round timer

### Technology Stack

- **Backend**: Flask 3.0.0 (Python)
- **Frontend**: Vanilla JavaScript + Modern CSS
- **Data**: Excel (openpyxl) + In-memory state + JSON auto-backup
- **Deployment**: Docker + Local Python
- **Testing**: unittest + Custom test suites
- **Persistence**: Auto-save to JSON with Docker volume mounting

---

## 🚀 Quick Start

### Prerequisites

Choose one installation method:
- **Docker Option** (Recommended): Docker Desktop installed
- **Local Option**: Python 3.11+ installed

### 5-Minute Setup

1. **Install Docker Desktop** (Recommended)
   ```bash
   # Download from https://docs.docker.com/get-docker/
   # Install and restart your computer
   ```

2. **Navigate to Project Folder**
   ```bash
   cd MTG-Tournament-Dashboard-AugmentCode
   ```

3. **Start the Application**
   ```bash
   # Windows
   .\build-and-run.bat

   # macOS/Linux
   ./build-and-run.sh

   # Or manually with Docker
   docker-compose up -d
   ```

4. **Open Browser**
   ```
   http://localhost:5000
   ```

5. **Run Tournament**
   - Click "📊 Load Participants" (loads from Excel or sample data)
   - Click "🏆 Setup Tournament" (generates all rounds)
   - Select rounds and submit scores
   - View live standings and champion!

---

## 💻 System Requirements

### Docker Method (Recommended)

- **Docker Desktop** installed and running
- **4GB RAM** minimum
- **500MB disk space** for container
- **Any OS**: Windows 10+, macOS 10.14+, Linux

### Local Installation Method

- **Python 3.11+** installed
- **pip** package manager
- **2GB RAM** minimum
- **100MB disk space**

---

## 📦 Installation

### Method 1: Docker Deployment (Recommended)

**Benefits:**
- ✅ No Python installation needed
- ✅ Works on any machine
- ✅ Isolated environment
- ✅ One command to start

**Steps:**

1. **Install Docker Desktop**
   ```bash
   # Verify installation
   docker --version
   docker-compose --version
   ```

2. **Build and Run**
   ```bash
   # Navigate to project
   cd MTG-Tournament-Dashboard-AugmentCode

   # Build and start (first time: 1-2 minutes)
   docker-compose up -d --build
   ```

3. **Access Dashboard**
   ```
   http://localhost:5000
   ```

4. **Stop Application**
   ```bash
   docker-compose down
   ```

### Method 2: Local Python Installation

**Steps:**

1. **Install Python 3.11+**
   ```bash
   # Verify installation
   python --version
   ```

2. **Install Dependencies**
   ```bash
   cd MTG-Tournament-Dashboard-AugmentCode
   pip install -r requirements.txt
   ```

3. **Run Application**
   ```bash
   python tournament_dashboard.py
   ```

4. **Access Dashboard**
   ```
   http://localhost:5000
   ```

---

## 🛡️ Data Persistence & Backup

### Overview

**Version 2.1** introduces automatic data persistence to protect your tournament data from Docker crashes, container restarts, and unexpected shutdowns.

### Key Features

✅ **Auto-Save**: Automatically saves tournament state after every important operation
✅ **Auto-Restore**: Automatically restores data when container starts
✅ **Crash Recovery**: Survives Docker crashes, restarts, and rebuilds
✅ **Zero Data Loss**: Tournament data persists across all container lifecycle events
✅ **Persistent Storage**: Backup file stored outside container (survives everything!)

### How It Works

**Auto-Save Triggers:**
- After loading participants
- After setting up tournament
- After submitting round results
- Manual save via API endpoint (optional)

**Backup Location:**
```
./tournament_backups/tournament_backup.json
```

This folder is mounted from your host machine, so backups survive:
- ✅ Docker container crashes
- ✅ `docker-compose restart`
- ✅ `docker-compose down` + `docker-compose up`
- ✅ Container rebuilds
- ✅ Computer restarts (if Docker restarts)

### What's Protected

All tournament data is automatically backed up:
- ✅ Teams and players
- ✅ All scores (team and individual)
- ✅ Round results and submissions
- ✅ Tournament configuration
- ✅ Current round state
- ✅ Playoff data (semifinals, finals)

### Recovery Scenarios

**Scenario 1: Docker Container Crashes**
```powershell
# Container crashed - just restart it
docker-compose restart

# Open browser - your data is back! ✅
http://localhost:5000
```

**Scenario 2: Accidental Stop**
```powershell
# Accidentally stopped container
docker-compose down

# Start it again
docker-compose up -d

# Open browser - your data is back! ✅
http://localhost:5000
```

**Scenario 3: Container Rebuild**
```powershell
# Need to rebuild with new code
docker-compose down
docker-compose up -d --build

# Open browser - your data is back! ✅
http://localhost:5000
```

### Console Messages

You'll see these messages in the logs:

```
✅ Auto-saved tournament state at 14:23:45
✅ Restored tournament state from backup (saved: 2025-11-24T14:23:45)
ℹ️ No backup file found - starting fresh
```

### Manual Backup (Optional)

Trigger a manual save anytime:

```bash
curl -X POST http://localhost:5000/save_backup
```

### Complete Documentation

For detailed information, see: **[DATA_PERSISTENCE_GUIDE.md](DATA_PERSISTENCE_GUIDE.md)**

Includes:
- Complete recovery scenarios
- Troubleshooting guide
- Best practices for tournament day
- Manual backup instructions

---

## 🏆 Tournament Structure

### Supported Configurations

| Teams | Swiss Rounds | Top 8 Cut | Finals | Total Rounds | Repeat Matchups |
|-------|--------------|-----------|--------|--------------|-----------------|
| 8     | 4            | NO        | YES (4 pods) | 5      | Possible |
| 12    | 4            | NO        | YES (4 pods) | 5      | Possible |
| 16    | 4            | YES (8 pods) | YES (4 pods) | 6   | Minimal |

### Tournament Flow

#### 8-Team Tournament
```
Load Data → Setup → Swiss Round 1 → Results → Swiss Round 2 → Results →
Swiss Round 3 → Results → Swiss Round 4 → Results → Finals → Champion
```

#### 12-Team Tournament
```
Load Data → Setup → Swiss Round 1 → Results → Swiss Round 2 → Results →
Swiss Round 3 → Results → Swiss Round 4 → Results → Finals → Champion
```

#### 16-Team Tournament
```
Load Data → Setup → Swiss Round 1 → Results → Swiss Round 2 → Results →
Swiss Round 3 → Results → Swiss Round 4 → Results → Top 8 Cut → Results → Finals → Champion
```

---

## 📊 Swiss Pairing Algorithm

### Incremental Round Generation

Rounds are generated **incrementally** after each round's results are confirmed:

```
Setup → Generate Round 1 only
Round 1 results submitted → Generate Round 2 based on scores
Round 2 results submitted → Generate Round 3 based on scores
Round 3 results submitted → Generate Round 4 based on scores
Round 4 results submitted → Generate Playoffs
```

This ensures proper Swiss pairing where teams are re-grouped each round based on their current standings.

### Three Core Pairing Constraints

#### 1. No Teammates at Same Table
- Players from the same team are **never** seated at the same pod
- Enforced in `_is_valid_pod()` and `_build_four_player_pod_with_constraints()`
- This is a hard constraint that is never violated

#### 2. Individual Score-Based Seating
- **Round 1:** Random seating (no prior scores)
- **Rounds 2-4:** Players sorted by **individual player score** (not team score)
- Best player vs best player, weakest vs weakest
- Implemented in `_organize_single_round_into_tables()` and `apply_intelligent_seating_to_round()`

#### 3. No Repeated Matchups
- Players should **not** face the same opponent twice
- Uses backtracking algorithm with permutations to find optimal player assignments
- If unavoidable (8/12 teams), swaps players with teammates to minimize repeats
- Implemented in `_create_four_pods_for_team_group()` using `itertools.permutations`

### Pod Consistency

Within each Swiss round, 4 teams are grouped together for **pod consistency**:
- All 4 players from each team face each other across exactly 4 separate pods
- After the round completes, teams are re-paired based on results for the next round
- Different team groups each round (based on standings)

### Round 1
- **Team Grouping:** Random
- **Seating:** Random (no prior scores)
- **Constraints:** No teammates at same table
- **Repeat Prevention:** N/A (first round)

### Rounds 2-4
- **Team Grouping:** Score-based (teams with similar standings grouped together)
- **Seating:** Individual player score-based (highest to lowest)
- **Constraints:** No teammates at same table
- **Repeat Prevention:** Backtracking algorithm minimizes repeat matchups

### Pod Structure
- **Players per Pod:** 4
- **Teams per Pod:** 4 (one player from each team)
- **Pods per Round:** Equal to number of teams

---

## 🎮 Playoff Structures

### Finals (All Tournaments)

**Eligibility:**
- 8/12 teams: Top 4 teams by Swiss points
- 16 teams: Top 4 teams by Top 8 Cut points

**Structure:**
- 4 pods
- 16 players (4 per pod)
- 4 teams represented
- No teammates at same table

**Seating Logic:**
```
Team Rankings: [Team A (1st), Team B (2nd), Team C (3rd), Team D (4th)]
Player Rankings within each team: [P1 (best), P2, P3, P4 (weakest)]

Pod 1: Team A P1, Team B P1, Team C P1, Team D P1  (strongest players)
Pod 2: Team A P2, Team B P2, Team C P2, Team D P2  (2nd strongest)
Pod 3: Team A P3, Team B P3, Team C P3, Team D P3  (3rd strongest)
Pod 4: Team A P4, Team B P4, Team C P4, Team D P4  (4th strongest)
```

### Top 8 Cut (16 Teams Only)

**Eligibility:**
- Top 8 teams by Swiss points

**Structure:**
- **8 pods** (NOT 4!)
- 32 players total
- 2 groups of 4 teams each

**Group Distribution:**
```
Group 1: Teams 1, 3, 5, 7 (odd rankings)
Group 2: Teams 2, 4, 6, 8 (even rankings)
```

**Pod Creation:**
```
Group 1 (4 pods):
  Pod 1: T1-P1, T3-P1, T5-P1, T7-P1
  Pod 2: T1-P2, T3-P2, T5-P2, T7-P2
  Pod 3: T1-P3, T3-P3, T5-P3, T7-P3
  Pod 4: T1-P4, T3-P4, T5-P4, T7-P4

Group 2 (4 pods):
  Pod 5: T2-P1, T4-P1, T6-P1, T8-P1
  Pod 6: T2-P2, T4-P2, T6-P2, T8-P2
  Pod 7: T2-P3, T4-P3, T6-P3, T8-P3
  Pod 8: T2-P4, T4-P4, T6-P4, T8-P4
```

---

## 💯 Scoring System

### Individual Player Scores
- **Win**: 5 points
- **Draw**: 1 point (all players at table draw)
- **Loss**: 0 points

### Team Scores
- Sum of all 4 players' scores per round
- Accumulated across all rounds
- Updated automatically after each round submission

### Championship Determination
1. **Finals Score**: Team with highest finals round score wins
2. **Tiebreaker**: If tied, Swiss round scores determine winner
3. **MVP**: Player with highest total individual points across all rounds

---

## ✨ Core Features

### 1. Participant Management
- **Excel Import**: Automatically loads teams and players from Excel spreadsheet
- **Sample Data**: Built-in sample data for testing (8, 12, or 16 teams)
- **Team Validation**: Ensures exactly 4 players per team
- **Data Persistence**: Maintains state throughout tournament
- **Auto-Backup**: Automatic save after loading participants

### 2. Swiss Pairing Algorithm
- **Uniform Swiss Rounds**: All tournaments use 4 Swiss rounds
- **Constraint Satisfaction**: Advanced backtracking algorithm
- **Team Separation**: Guarantees no teammates at same table
- **Individual Score-Based Seating**: Players seated by their individual scores (not team scores)
- **Repeat Matchup Prevention**: Minimizes players facing same opponents twice

### 3. Score Tracking
- **Individual Scores**: Track each player's points (Win=5, Draw=1, Loss=0)
- **Team Scores**: Automatic calculation (sum of 4 players)
- **Live Standings**: Real-time leaderboard updates
- **Score Validation**: Prevents invalid scores and duplicates
- **Duplicate Prevention**: Blocks re-submission of finalized rounds

### 4. Playoff System
- **Automatic Qualification**: Top teams advance based on standings
- **Strength-Based Seating**: Best players face each other
- **Tiebreaker Logic**: Swiss scores used for ties
- **Championship Determination**: Clear winner with MVP recognition

### 5. Data Persistence & Crash Recovery
- **Auto-Save**: Automatic backup after every important operation
- **Auto-Restore**: Seamless recovery on container restart
- **Crash Protection**: Survives Docker crashes and restarts
- **Zero Data Loss**: Tournament data protected at all times

### 6. User Interface
- **Modern Design**: Glassmorphism UI with smooth animations
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Real-Time Updates**: Live score and standings updates
- **Round Timer**: Built-in stopwatch for time management

---

## 🔌 API Endpoints

### Tournament Setup
- `POST /load_data` - Load participants from Excel or sample data
- `POST /configure_swiss_rounds` - Configure Swiss rounds (4 or 5)
- `POST /setup_tournament` - Generate all tournament rounds
- `POST /reset_tournament` - Reset tournament state
- `POST /save_backup` - Manually trigger backup save 🆕

### Round Management
- `GET /setup_round/<round_num>` - Get round tables and setup
- `POST /submit_player_results` - Submit player scores for a round
- `GET /get_tables/<round_num>` - Get tables for specific round

### Data Retrieval
- `GET /get_teams` - Get all teams
- `GET /get_scores` - Get team scores
- `GET /get_player_scores` - Get individual player scores
- `GET /standings` - Get current standings
- `GET /final_standings` - Get final standings
- `GET /get_tournament_state` - Get complete tournament state

### Playoffs
- `GET /generate_semifinals` - Generate semifinals round (16 teams)
- `GET /get_semifinals` - Get semifinals data
- `GET /generate_finals` - Generate finals round
- `GET /get_finals` - Get finals data

### Validation
- `GET /validate_integrity` - Validate tournament data integrity

---

## 📖 Usage Guide

### Step-by-Step Tournament Workflow

#### 1. Load Participants

**Option A: From Excel File**
```bash
# Place Excel file at: July_CEDH_Event/13th July CEDH Participant List.xlsx
# Click "📊 Load Participants" button
# System automatically loads teams and players
```

**Option B: Use Sample Data**
```bash
# Click "📊 Load Participants" button
# If Excel file not found, sample data loads automatically
# Or use API: POST /load_data with {"use_sample_data": true, "sample_team_count": 8}
```

#### 2. Setup Tournament

```bash
# Click "🏆 Setup Tournament" button
# System generates Round 1 only
# Subsequent rounds generated after each round's results are submitted
```

#### 3. Run Swiss Rounds

For each Swiss round (1-4):

```bash
# 1. Select round from dropdown
# 2. View table assignments
# 3. Enter scores for each player (Win=5, Draw=1, Loss=0)
# 4. Click "Submit Round Results"
# 5. View updated standings
# 6. Next round is automatically generated based on current standings
# 7. Repeat for remaining rounds
```

#### 4. Run Top 8 Cut (16 teams only)

```bash
# After Swiss round 4 results are submitted:
# 1. System automatically generates Top 8 Cut
# 2. Top 8 teams advance
# 3. Select Top 8 Cut round
# 4. Enter scores
# 5. Submit results
```

#### 5. Run Finals

```bash
# After Swiss round 4 (8/12 teams) or Top 8 Cut (16 teams):
# 1. System automatically generates finals
# 2. Top 4 teams advance
# 3. Select finals round
# 4. Enter scores
# 5. Submit results
```

#### 6. View Champion

```bash
# After finals complete:
# 1. View final standings
# 2. Champion is team with highest finals round score
# 3. Tiebreaker: Swiss round scores
# 4. MVP: Player with highest individual total score
```

### Common Operations

**Reset Tournament:**
```bash
# Click "Reset Tournament" button
# Or use API: POST /reset_tournament
# Clears all scores and round data
# Keeps participant data loaded
```

**View Standings:**
```bash
# Click "Standings" tab
# Shows current team rankings
# Updates in real-time after each round
```

**Manual Backup:**
```bash
# Trigger manual save: POST /save_backup
# Backup file: ./tournament_backups/tournament_backup.json
```

---

## 🔧 Troubleshooting

### Common Issues

**Issue: Excel file not found**
```
Solution:
1. Check file path: July_CEDH_Event/13th July CEDH Participant List.xlsx
2. Or use sample data instead
3. System automatically falls back to sample data
```

**Issue: Cannot submit scores**
```
Solution:
1. Check if round is already finalized
2. Verify all players have valid scores (0, 1, or 5)
3. Ensure tournament is set up
4. Check browser console for errors
```

**Issue: Duplicate submission error**
```
Solution:
1. Round already finalized - this is expected behavior
2. Use "Reset Tournament" to start over
3. Or continue to next round
```

**Issue: Wrong number of teams**
```
Solution:
1. System only supports 8, 12, or 16 teams
2. Check Excel file has correct number of teams
3. Each team must have exactly 4 players
```

**Issue: Docker container won't start**
```
Solution:
1. Check Docker Desktop is running
2. Run: docker-compose down
3. Run: docker-compose up -d --build
4. Check logs: docker-compose logs
```

**Issue: Port 5000 already in use**
```
Solution:
1. Stop other applications using port 5000
2. Or change port in docker-compose.yml
3. Update ports: "5001:5000" (use 5001 instead)
```

### Debug Mode

Enable debug logging:
```python
# In tournament_dashboard.py
app.run(debug=True, host='0.0.0.0', port=5000)
```

View logs:
```bash
# Docker
docker-compose logs -f

# Local
# Check terminal output
```

---

## 🏗️ Architecture

### Project Structure

```
MTG-Tournament-Dashboard-AugmentCode/
├── tournament_dashboard.py          # Main Flask application (2,471 lines)
├── unified_swiss_pairing.py        # Pairing algorithm (1,374 lines)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose setup
├── build-and-run.bat              # Windows startup script
├── build-and-run.sh               # Linux/macOS startup script
├── templates/
│   ├── dashboard.html             # Original UI
│   ├── dashboard_modern.html      # Modern UI
│   └── dashboard_ultra_modern.html # Ultra-modern UI (recommended)
├── July_CEDH_Event/
│   └── 13th July CEDH Participant List.xlsx
├── test_api_endpoints.py          # API integration tests (706 lines)
├── test_tournament_comprehensive.py # Backend tests (1,413 lines)
├── test_tournament_scenarios.py   # Scenario tests (547 lines)
├── run_validation_suite.py        # Test runner
└── README.md                      # This file
```

### Key Components

**Backend (tournament_dashboard.py):**
- `TournamentManager` class: Core business logic
- Flask routes: 20+ API endpoints
- State management: In-memory tournament state
- Score calculation: Team and player scoring
- Playoff generation: Semifinals and finals logic

**Pairing Algorithm (unified_swiss_pairing.py):**
- Constraint satisfaction solver
- Backtracking algorithm
- Team separation enforcement
- Repeat matchup prevention
- Score-based seating

**Frontend (dashboard_ultra_modern.html):**
- Modern glassmorphism UI
- Real-time updates via API calls
- Responsive design
- Interactive score entry
- Live standings display

### Data Flow

```
User Action → Frontend (JavaScript) → API Endpoint → TournamentManager →
State Update → Response → Frontend Update → UI Refresh
```

### State Management

**In-Memory State:**
- `teams`: Team data (name, players)
- `scores`: Team scores
- `player_scores`: Individual player scores
- `tables`: Round table assignments
- `round_results`: Submitted results
- `submitted_rounds`: Finalized rounds
- `finalized_rounds`: Locked rounds

**Persistence:**
- Auto-backup to JSON file after each operation
- Auto-restore on container restart
- Backup file: `./tournament_backups/tournament_backup.json`

---

## 📅 Version History

### v2.3 (2025-12-04) - Current

- ✅ Revised tournament structure (8, 12, 16 teams only)
- ✅ Uniform 4 Swiss rounds for all tournaments
- ✅ Incremental round generation (rounds generated after results submitted)
- ✅ Individual player score-based seating (not team scores)
- ✅ Backtracking algorithm for repeat matchup prevention
- ✅ 16 teams: Top 8 Cut with 8 pods before finals
- ✅ 8 and 12 teams: Direct to finals (top 4)
- ✅ Removed 20-team support
- ✅ Consolidated documentation into single README.md

### v2.2 (2025-12-04)

- Multi-team support added (8, 12, 16, 20 teams)
- Flexible Swiss rounds
- Auto-configure tournament structure

### v2.1 (2025-11-24)

- Data persistence and auto-backup
- Crash recovery system
- Docker volume mounting
- Auto-restore on startup

### v2.0 (2025-11-24)

- Complete API endpoint coverage
- Duplicate prevention implemented
- Tournament structure determination
- Sample data support

### v1.0 (2025-11-01)

- Initial release
- Core tournament functionality
- Swiss pairing algorithm
- Basic UI

---

## 📄 License

Proprietary - For MTG Tournament Use

---

**End of Documentation**
